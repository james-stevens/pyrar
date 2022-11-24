#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import os
import sys
import json
import httpx
import flask

import zonelib
import parsexml
import lib.validate as validate
from lib.log import log as log, init as log_init
import lib.fileloader as fileloader
import lib.policy as policy
import users
import lib.mysql
import lib.event
from lib.event import event

from inspect import currentframe as czz, getframeinfo as gzz

http_heads = {}

HEADER = {
    'Access-Control-Allow-Origin': '*',
    'Content-type': 'application/json',
    'Accept': 'application/json'
}


def fees_one(action, years):
    return {
        "@name": action,
        "fee:period": {
            "@unit": "y",
            "#text": str(years),
        }
    }


def xml_check_with_fees(domobj, years, which):
    fees_extra = [fees_one(name, years) for name in which]
    return {
        "check": {
            "domain:check": {
                "@xmlns:domain": xmlns[domobj.provider]["domain"],
                "domain:name": domobj.names
            }
        },
        "extension": {
            "fee:check": {
                "@xmlns:fee": xmlns[domobj.provider]["fee"],
                "fee:currency": "USD",
                "fee:command": fees_extra
            }
        }
    }


my_policy = policy.Policy()
log_init(my_policy.policy("facility_python_code"),
         my_policy.policy("log_python_code"))

tld_lib = zonelib.ZoneLib()
tld_lib.check_for_new_files()
xmlns = tld_lib.make_xmlns()
clients = {p: httpx.Client() for p in tld_lib.ports}

lib.mysql.connect("webui")


def check_ok(name):
    if not tld_lib.supported_tld(name):
        return "Unsupported TLD"
    if not validate.is_valid_fqdn(name):
        return "Domain failed validation"
    return None


class DomainName:
    def __init__(self, domain):
        self.names = None
        self.err = None
        self.provider = None
        self.url = None

        if isinstance(domain, str):
            if domain.find(",") >= 0:
                self.process_list(domain.split(","))
            else:
                self.process_string(domain)

        if isinstance(domain, list):
            self.process_list(domain)

    def process_string(self, domain):
        name = domain.lower()
        if (err := check_ok(name)) is None:
            self.names = name
        else:
            self.err = err
            self.names = None
        self.provider, self.url = tld_lib.http_req(name)

    def process_list(self, domain):
        self.names = []
        for dom in domain:
            name = dom.lower()
            if (err := check_ok(name)) is None:
                self.names.append(name)
                if self.provider is None:
                    self.provider, self.url = tld_lib.http_req(name)
                else:
                    prov, __ = tld_lib.http_req(name)
                    if prov != self.provider:
                        self.err = "ERROR: Split providers request"
                        self.names = None
                        return
            else:
                self.err = err
                self.names = None
                return


def http_price_domains(domobj, years, which):

    if domobj.provider is None or domobj.url is None:
        return 400, "Unsupported TLD"

    resp = clients[domobj.provider].post(domobj.url,
                                         json=xml_check_with_fees(
                                             domobj, years, which),
                                         headers=HEADER)

    if resp.status_code < 200 or resp.status_code > 299:
        return 400, "Invalid HTTP Response from parent"

    try:
        return 200, json.loads(resp.content)
    except ValueError as err:
        log(f"{resp.status_code} === {resp.content.decode('utf8')}",
            gzz(czz()))
        log(f"**** JSON FAILED TO PARSE ***** {err}", gzz(czz()))
        return 400, "Returned JSON Parse Error"

    return 400, "Unexpected Error"


def check_and_parse(domobj):
    ret, out_js = http_price_domains(domobj, 1, ["create", "renew"])
    if ret != 200:
        return abort(ret, out_js)

    xml_p = parsexml.XmlParser(out_js)
    code, ret_js = xml_p.parse_check_message()

    if not code == 1000:
        return abort(400, ret_js)

    tld_lib.multiply_values(ret_js)
    tld_lib.sort_data_list(ret_js, is_tld=False)

    return flask.jsonify(ret_js)


def abort(err_no, message):
    response = flask.jsonify({'error': message})
    response.status_code = err_no
    return response


application = flask.Flask("EPP Registrar")


def start_req():
    global http_heads
    http_heads = dict(flask.request.headers)
    tld_lib.check_for_new_files()
    lib.event.http_start("webui", flask.request.remote_addr, 99)


@application.route('/api/v1.0/config', methods=['GET'])
def get_config():
    start_req()
    ret = {
        "providers": tld_lib.zone_send,
        "zones": tld_lib.return_zone_list(),
        "policy": my_policy.data()
    }
    return flask.jsonify(ret)


@application.route('/api/v1.0/zones', methods=['GET'])
def get_supported_zones():
    start_req()
    return flask.jsonify(tld_lib.return_zone_list())


@application.route('/api/v1.0/hello', methods=['GET'])
def hello():
    start_req()
    return "Hello World\n"


@application.route('/api/v1.0/users/register', methods=['POST'])
def users_register():
    start_req()
    if flask.request.json is None:
        return abort(400, "No JSON posted")

    user_agent = http_heads[
        "User-Agent"] if "User-Agent" in http_heads else "Unknown"
    ret, val = users.register(flask.request.json, user_agent)
    if not ret:
        return abort(400, val)
    return flask.jsonify(val)


@application.route('/api/v1.0/domain/check', methods=['POST', 'GET'])
def rest_domain_price():
    start_req()
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

    dom_obj = DomainName(dom)

    if dom_obj.names is None:
        if dom_obj.err is not None:
            return abort(400, dom_obj.err)
        return abort(400, "Invalid domain name")

    return check_and_parse(dom_obj)


def run_one(domain):
    domobj = DomainName(domain)
    if domobj.names is None:
        sys.exit(1)

    ret, out_js = http_price_domains(
        domobj, 1, ["create", "renew", "transfer", "restore"])

    if ret != 200:
        log(f"ERROR: {ret} {out_js}", gzz(czz()))
    else:
        xml_p = parsexml.XmlParser(out_js)
        code, ret_js = xml_p.parse_check_message()
        if code == 1000:
            tld_lib.multiply_values(ret_js)
        print(">>>TEST>>>", code, json.dumps(ret_js, indent=3))
    for client in clients:
        clients[client].close()


if __name__ == "__main__":
    log.debug = True
    if len(sys.argv) > 1:
        x = sys.argv[1].lower()
        print("====>> RUN ONE", x, "=>", sys.argv[1])
        run_one(x)
        sys.exit(0)

    application.run()
