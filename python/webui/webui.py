#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
import sys
import json
import httpx
import flask

from lib.providers import tld_lib
from lib.log import log, debug, init as log_init
from lib.policy import this_policy as policy
import users
from lib import mysql as sql
import domains

from inspect import currentframe as czz, getframeinfo as gzz

SESSION_TAG = "X-Session-Code"
SESSION_TAG_LOWER = SESSION_TAG.lower()

log_init(policy.policy("facility_python_code"),
         with_logging=policy.policy("log_python_code"))

sql.connect("webui")
application = flask.Flask("EPP Registrar")


class WebuiReq:
    """ data unique to each request to keep different users data separate """
    def __init__(self):
        tld_lib.check_for_new_files()
        self.sess_code = None
        self.user_id = None
        self.headers = {
            item.lower(): val
            for item, val in dict(flask.request.headers).items()
        }
        self.user_agent = self.headers[
            "user-agent"] if "user-agent" in self.headers else "Unknown"

        if SESSION_TAG_LOWER in self.headers:
            logged_in, check_sess_data = users.check_session(
                self.headers[SESSION_TAG_LOWER], self.user_agent)
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
        return {
            "from_where": flask.request.remote_addr,
            "user_id": self.user_id,
            "who_did_it": "webui"
        }

    def abort(self, data, err_no=400):
        return self.response({"error": data}, err_no)

    def response(self, data, code=200):
        resp = flask.make_response(data, code)
        if self.sess_code is not None:
            resp.headers[SESSION_TAG] = self.sess_code
        return resp

    def event(self, data, frameinfo):
        data["program"] = frameinfo.filename.split("/")[-1]
        data["function"] = frameinfo.function
        data["line_num"] = frameinfo.lineno
        data["when_dt"] = None
        data.update(self.base_event)
        sql.sql_insert("events", data)


@application.route('/api/v1.0/config', methods=['GET'])
def get_config():
    req = WebuiReq()
    ret = {
        "providers": tld_lib.zone_send,
        "zones": tld_lib.return_zone_list(),
        "policy": policy.data()
    }
    return req.response(ret)


@application.route('/api/v1.0/zones', methods=['GET'])
def get_supported_zones():
    req = WebuiReq()
    return req.response(tld_lib.return_zone_list())


@application.route('/api/v1.0/hello', methods=['GET'])
def hello():
    req = WebuiReq()
    return req.response("Hello World\n")


@application.route('/api/v1.0/users/domains', methods=['GET'])
def users_domains():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort("Not logged in")

    ret, doms = sql.sql_select("domains", {"user_id": req.user_id},order_by="name")
    if ret is None:
        return req.abort("Failed to load domains")
    req.user_data["domains"] = doms

    return req.response(req.user_data)


@application.route('/api/v1.0/users/details', methods=['GET'])
def users_details():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort("Not logged in")

    ret, user = sql.sql_select_one("users", {"user_id": req.user_id})
    if ret is None:
        return req.abort("Failed to load user account")

    users.secure_user_data(user)
    req.user_data["user"] = user

    return req.response(req.user_data)


@application.route('/api/v1.0/users/login', methods=['POST'])
def users_login():
    req = WebuiReq()
    if flask.request.json is None:
        return req.abort("No JSON posted")

    ret, data = users.login(flask.request.json, req.user_agent)
    if not ret or not data:
        return req.abort("Login failed")

    req.parse_user_data(ret, data)
    return req.response(data)


@application.route('/api/v1.0/users/logout', methods=['GET'])
def users_logout():
    req = WebuiReq()
    if not req.sess_code:
        return req.abort("Not logged in")
    users.logout(req.sess_code, req.user_id, req.user_agent)
    req.sess_code = None
    return req.response("logged-out")


@application.route('/api/v1.0/users/register', methods=['POST'])
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
    req.event(
        {
            "user_id": user_id,
            "notes": "User registered",
            "event_type": "new_user"
        }, gzz(czz()))

    return req.response(val)


@application.route('/api/v1.0/domain/check', methods=['POST', 'GET'])
def rest_domain_price():
    req = WebuiReq()
    if flask.request.json is not None:
        dom = flask.request.json["domain"]
        if not isinstance(dom, str) and not isinstance(dom, list):
            return req.abort("Unsupported data type for domain")
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

    dom_obj = domains.DomainName(dom)

    if dom_obj.names is None:
        if dom_obj.err is not None:
            return req.abort(dom_obj.err)
        return req.abort("Invalid domain name")

    try:
        ret = domains.check_and_parse(dom_obj)
        return req.response(ret)
    except Exception as exc:
        debug(str(exc), gzz(czz()))
        return req.abort("Domain check failed")


if __name__ == "__main__":
    log_init(policy.policy("facility_python_code"),
             debug=True,
             with_logging=policy.policy("log_python_code"))
    application.run()
    domains.close_epp_sess()
