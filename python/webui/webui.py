#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
import sys
import json
import httpx
import flask
import bcrypt

from lib import registry
from lib.log import log, debug, init as log_init
from lib.policy import this_policy as policy
import users
from lib import mysql as sql
import domains

from inspect import currentframe as czz, getframeinfo as gzz

HTML_CODE_ERR = 499
HTML_CODE_OK = 200

NOT_LOGGED_IN = "Not logged in or login timed-out"

SESSION_TAG = "X-Session-Code"
SESSION_TAG_LOWER = SESSION_TAG.lower()

log_init(policy.policy("facility_python_code"), with_logging=policy.policy("log_python_code"))
sql.connect("webui")
application = flask.Flask("EPP Registrar")
registry.start_up()
domains.start_up()


class WebuiReq:
    """ data unique to each request to keep different users data separate """
    def __init__(self):
        registry.tld_lib.check_for_new_files()
        self.sess_code = None
        self.user_id = None
        self.headers = {item.lower(): val for item, val in dict(flask.request.headers).items()}
        self.user_agent = self.headers["user-agent"] if "user-agent" in self.headers else "Unknown"

        if SESSION_TAG_LOWER in self.headers:
            logged_in, check_sess_data = users.check_session(self.headers[SESSION_TAG_LOWER], self.user_agent)
            self.parse_user_data(logged_in, check_sess_data)

        self.base_event = self.set_base_event()

    def parse_user_data(self, logged_in, check_sess_data):
        if not logged_in or "session" not in check_sess_data:
            return

        self.user_data = check_sess_data
        self.sess_code = check_sess_data["session"]
        self.user_id = check_sess_data['user_id']
        debug(f"Logged in as {self.user_id}", gzz(czz()))

    def set_base_event(self):
        ip_addr = flask.request.remote_addr
        if "x-forwaded-for" in self.headers:
            ip_addr = self.headers["x-forwaded-for"]
        return {"from_where": ip_addr, "user_id": self.user_id, "who_did_it": "webui"}

    def abort(self, data):
        return self.response({"error": data}, HTML_CODE_ERR)

    def response(self, data, code=HTML_CODE_OK):
        resp = flask.make_response(flask.jsonify(data), code)
        resp.charset = 'utf-8'
        if self.sess_code is not None:
            resp.headers[SESSION_TAG] = self.sess_code
        return resp

    def event(self, data, frameinfo):
        data["program"] = frameinfo.filename.split("/")[-1]
        data["function"] = frameinfo.function
        data["line_num"] = frameinfo.lineno
        data["when_dt"] = None
        for item in self.base_event:
            if item not in data:
                data[item] = self.base_event[item]
        sql.sql_insert("events", data)


@application.route('/pyrar/v1.0/config', methods=['GET'])
def get_config():
    req = WebuiReq()
    ret = {
        "registry": registry.tld_lib.zone_send,
        "zones": registry.tld_lib.return_zone_list(),
        "policy": policy.data()
    }
    return req.response(ret)


@application.route('/pyrar/v1.0/zones', methods=['GET'])
def get_supported_zones():
    req = WebuiReq()
    return req.response(registry.tld_lib.return_zone_list())


@application.route('/pyrar/v1.0/hello', methods=['GET'])
def hello():
    req = WebuiReq()
    return req.response("Hello World\n")


@application.route('/pyrar/v1.0/users/domains', methods=['GET'])
def users_domains():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    ret, doms = sql.sql_select("domains", {"user_id": req.user_id}, order_by="name")
    if ret is None:
        return req.abort("Failed to load domains")
    req.user_data["domains"] = doms

    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/update', methods=['POST'])
def users_update():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if flask.request.json is None:
        return req.abort("No JSON posted")

    ret, user_data = users.update_user(req.user_id, flask.request.json)
    if not ret:
        return req.abort(user_data)

    req.user_data["user"] = user_data

    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/close', methods=['POST'])
def users_close():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if not users.check_password(req.user_id, flask.request.json):
        return req.abort("Password match failed")

    ok = sql.sql_update_one("users", "password=concat('CLOSED:',password),amended_dt=now()", {"user_id": req.user_id})

    if not ok:
        return req.abort("Close account failed")

    sql.sql_delete_one("session_keys", {"user_id": req.user_id})
    req.user_id = None
    req.sess_code = None

    return req.response("OK")


@application.route('/pyrar/v1.0/users/password', methods=['POST'])
def users_password():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if not users.check_password(req.user_id, flask.request.json):
        return req.abort("Password match failed")

    new_pass = bcrypt.hashpw(flask.request.json["new_password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    ok = sql.sql_update_one("users", {"password": new_pass, "amended_dt": None}, {"user_id": req.user_id})

    if not ok:
        return req.response("OK")

    return req.abort("Failed")


@application.route('/pyrar/v1.0/users/details', methods=['GET'])
def users_details():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    ret, user = sql.sql_select_one("users", {"user_id": req.user_id})
    if ret is None:
        return req.abort("Failed to load user account")

    users.secure_user_db_rec(user)
    req.user_data["user"] = user

    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/login', methods=['POST'])
def users_login():
    req = WebuiReq()
    if flask.request.json is None:
        return req.abort("No JSON posted")

    ret, data = users.login(flask.request.json, req.user_agent)
    if not ret or not data:
        return req.abort("Login failed")

    req.parse_user_data(ret, data)
    return req.response(data)


@application.route('/pyrar/v1.0/users/logout', methods=['GET'])
def users_logout():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    users.logout(req.sess_code, req.user_id, req.user_agent)

    req.sess_code = None
    req.user_id = None

    return req.response("logged-out")


@application.route('/pyrar/v1.0/users/register', methods=['POST'])
def users_register():
    req = WebuiReq()
    if flask.request.json is None:
        return req.abort("No JSON posted")

    ret, val = users.register(flask.request.json, req.user_agent)
    if not ret:
        return req.abort(val)

    debug("REGISTER " + str(val), gzz(czz()))

    user_id = val["user"]["user_id"]
    req.user_id = user_id
    req.sess_code = val["session"]
    req.base_event["user_id"] = user_id
    req.event({"notes": "User registered", "event_type": "new_user"}, gzz(czz()))

    return req.response(val)


@application.route('/pyrar/v1.0/domain/gift', methods=['POST'])
def domain_gift():
    return run_user_domain_task(domains.webui_gift_domain, "Gift", gzz(czz()))


@application.route('/pyrar/v1.0/domain/update', methods=['POST'])
def domain_update():
    return run_user_domain_task(domains.webui_update_domain, "Update", gzz(czz()))


@application.route('/pyrar/v1.0/domain/authcode', methods=['POST'])
def domain_authcode():
    return run_user_domain_task(domains.webui_set_auth_code, "setAuth", gzz(czz()))


def run_user_domain_task(domain_function, func_name, context):
    req = WebuiReq()
    if flask.request.json is None or not sql.has_data(flask.request.json, "name"):
        return req.abort("No JSON posted or domain is missing")

    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    ok, reply = domain_function(req, flask.request.json)

    if not ok:
        return req.abort(reply)

    notes = context.function
    if "dest_email" in flask.request.json:
        notes = f"Domain gifted from {req.user_id} to {flask.request.json['dest_email']}"

    req.event({"domain_id": flask.request.json["domain_id"], "notes": notes, "event_type": context.function}, context)
    if func_name == "Gift":
        req.event(
            {
                "user_id": reply["new_user_id"],
                "domain_id": flask.request.json["domain_id"],
                "notes": notes,
                "event_type": context.function
            }, context)

    return req.response(reply)


@application.route('/pyrar/v1.0/domain/check', methods=['POST', 'GET'])
def rest_domain_price():
    req = WebuiReq()
    num_yrs = 1
    qry_type = ["create", "renew"]

    if flask.request.json is not None:
        dom = flask.request.json["domain"]
        if not isinstance(dom, str) and not isinstance(dom, list):
            return req.abort("Unsupported data type for domain")
        if "num_years" in flask.request.json:
            num_yrs = int(flask.request.json["num_years"])
        if "qry_type" in flask.request.json:
            qry_type = flask.request.json["qry_type"].split(",")
    else:
        data = None
        if flask.request.method == "POST":
            data = flask.request.form
        if flask.request.method == "GET":
            data = flask.request.args
        if data is None or len(data) <= 0:
            return req.abort("No data sent")
        if (dom := data.get("domain")) is None:
            return req.abort("No domain sent")
        if (yrs := data.get("num_years")) is not None:
            num_yrs = int(yrs)
        if (qry := data.get("qry_type")) is not None:
            qry_type = qry.split(",")

    dom_obj = domains.DomainName(dom)

    if dom_obj.names is None:
        if dom_obj.err is not None:
            return req.abort(dom_obj.err)
        return req.abort("Invalid domain name")

    ok, reply = domains.get_domain_prices(dom_obj, num_yrs, qry_type, req.user_id)
    if ok:
        return req.response(reply)

    log("FAILED:" + str(ok) + ":" + str(reply) + ":" + str(dom_obj.names), gzz(czz()))
    return req.abort(reply)


if __name__ == "__main__":
    log_init(with_debug=True)
    application.run()
    domains.close_epp_sess()
