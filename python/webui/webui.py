#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
import sys
import json
import httpx
import flask

from zonelib import tld_lib
from lib.log import log as log, init as log_init
from lib.policy import this_policy as policy
import users
import lib.mysql
import domains

from inspect import currentframe as czz, getframeinfo as gzz


log_init(policy.policy("facility_python_code"),
         policy.policy("log_python_code"))

lib.mysql.connect("webui")
application = flask.Flask("EPP Registrar")


def abort(err_no, message):
    response = flask.jsonify({'error': message})
    response.status_code = err_no
    return response


class WebuiReq:
    """ data unique to each request to keep different users data separate """
    def __init__(self):
        tld_lib.check_for_new_files()
        self.base_event = {}
        self.base_event["from_where"] = flask.request.remote_addr
        self.base_event["user_id"] = 0
        self.base_event["who_did_it"] = "webui"
        self.headers = dict(flask.request.headers)
        self.user_agent = self.headers[
            "User-Agent"] if "User-Agent" in self.headers else "Unknown"

        if "X-Pyrar-Sess" in self.headers:
            self.logged_in, self.user_data = users.check_session(
                self.headers["X-Pyrar-Sess"], self.user_agent)
            if self.logged_in:
                print(">>>> LOGGED-IN",self.user_data["user"])

    def event(self, data, frameinfo):
        data["program"] = frameinfo.filename.split("/")[-1]
        data["function"] = frameinfo.function
        data["line_num"] = frameinfo.lineno
        data["when_dt"] = None
        data.update(self.base_event)
        lib.mysql.sql_insert("events", data)


@application.route('/api/v1.0/config', methods=['GET'])
def get_config():
    this_req = WebuiReq()
    ret = {
        "providers": tld_lib.zone_send,
        "zones": tld_lib.return_zone_list(),
        "policy": policy.data()
    }
    return flask.jsonify(ret)


@application.route('/api/v1.0/zones', methods=['GET'])
def get_supported_zones():
    this_req = WebuiReq()
    return flask.jsonify(tld_lib.return_zone_list())


@application.route('/api/v1.0/hello', methods=['GET'])
def hello():
    this_req = WebuiReq()
    return "Hello World\n"


@application.route('/api/v1.0/users/register', methods=['POST'])
def users_register():
    this_req = WebuiReq()
    if flask.request.json is None:
        return abort(400, "No JSON posted")

    ret, val = users.register(flask.request.json, this_req.user_agent)
    if not ret:
        return abort(400, val)

    user_id = val["user"]["user_id"]
    this_req.base_event["user_id"] = user_id
    this_req.event(
        {
            "user_id": user_id,
            "notes": "User registered",
            "event_type": "new_user"
        }, gzz(czz()))

    return flask.jsonify(val)


@application.route('/api/v1.0/domain/check', methods=['POST', 'GET'])
def rest_domain_price():
    this_req = WebuiReq()
    if flask.request.json is not None:
        dom = flask.request.json["domain"]
        if not isinstance(dom, str) and not isinstance(dom, list):
            return abort(400, "Unsupported data type for domain")
    else:
        data = None
        if flask.request.method == "POST":
            data = flask.request.form
        if flask.request.method == "GET":
            data = flask.request.args
        if data is None or len(data) <= 0:
            return abort(400, "No data sent")
        if (dom := data.get("domain")) is None:
            return abort(400, "No domain sent")

    dom_obj = domains.DomainName(dom)

    if dom_obj.names is None:
        if dom_obj.err is not None:
            return abort(400, dom_obj.err)
        return abort(400, "Invalid domain name")

    return domains.check_and_parse(dom_obj)


if __name__ == "__main__":
    application.run()
    domains.close_epp_sess()
