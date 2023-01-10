#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import inspect
import flask

from librar import registry
from librar import misc
from librar import validate
from librar import passwd
from librar import pdns
from librar import sigprocs
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy
from librar import mysql as sql
from webui import users
from webui import domains
from webui import basket
from mailer import spool_email

from webui import pay_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from webui.pay_plugins import *


HTML_CODE_ERR = 499
HTML_CODE_OK = 200

NOT_LOGGED_IN = "Not logged in or login timed-out"

SESSION_TAG = "X-Session-Code"
SESSION_TAG_LOWER = SESSION_TAG.lower()

# remove these columns before transmitting to user
REMOVE_TO_SECURE = {
    "user": ["password", "two_fa", "password_reset"],
    "orders": ["price_charged", "currency_charged"],
    "transactions": ["sales_item_id"]
}

log_init(policy.policy("facility_python_code"), with_logging=policy.policy("log_python_code"))
sql.connect("webui")
application = flask.Flask("EPP Registrar")
registry.start_up()
pdns.start_up()

site_currency = policy.policy("currency")
if not validate.valid_currency(site_currency):
    raise ValueError("ERROR: Main policy.currency is not set up correctly")


class WebuiReq:
    """ data unique to each request to keep different users data separate """
    def __init__(self):
        registry.tld_lib.check_for_new_files()
        self.sess_code = None
        self.user_id = None
        self.user_data = None
        self.post_js = flask.request.json
        self.headers = {item.lower(): val for item, val in dict(flask.request.headers).items()}
        self.user_agent = self.headers["user-agent"] if "user-agent" in self.headers else "Unknown"

        if SESSION_TAG_LOWER in self.headers:
            logged_in, check_sess_data = users.check_session(self.headers[SESSION_TAG_LOWER], self.user_agent)
            self.parse_user_data(logged_in, check_sess_data)

        self.base_event = self.set_base_event()
        self.is_logged_in = (self.user_id is not None and self.sess_code is not None)

    def parse_user_data(self, logged_in, check_sess_data):
        if not logged_in or "session" not in check_sess_data:
            return

        self.user_data = check_sess_data
        self.sess_code = check_sess_data["session"]
        self.user_id = check_sess_data['user_id']
        debug(f"Logged in as {self.user_id}")

    def set_base_event(self):
        ip_addr = flask.request.remote_addr
        if "x-forwaded-for" in self.headers:
            ip_addr = self.headers["x-forwaded-for"]
        return {"from_where": ip_addr, "user_id": self.user_id, "who_did_it": "webui"}

    def abort(self, data):
        return self.response({"error": data}, HTML_CODE_ERR)

    def secure_user_data(self):
        if self.user_data is None:
            return
        for table in REMOVE_TO_SECURE:
            if table in self.user_data and isinstance(self.user_data[table], dict):
                for column in REMOVE_TO_SECURE[table]:
                    if column in self.user_data[table]:
                        del self.user_data[table][column]

    def response(self, data, code=HTML_CODE_OK):
        self.secure_user_data()

        resp = flask.make_response(flask.jsonify(data), code)
        resp.charset = 'utf-8'
        if self.sess_code is not None:
            resp.headers[SESSION_TAG] = self.sess_code
        return resp

    def event(self, data):
        context = inspect.stack()[1]
        data["program"] = context.filename.split("/")[-1]
        data["function"] = context.function
        data["line_num"] = context.lineno
        data["when_dt"] = None
        for item, evt_data in self.base_event.items():
            if item not in data:
                data[item] = evt_data
        sql.sql_insert("events", data)


@application.route('/pyrar/v1.0/config', methods=['GET'])
def get_config():
    req = WebuiReq()
    return req.response({
        "default_currency": policy.policy("currency"),
        "registry": registry.tld_lib.regs_send(),
        "zones": registry.tld_lib.return_zone_list(),
        "status": misc.DOMAIN_STATUS,
        "payments": { pay:pay_data["desc"] for pay, pay_data in pay_handler.pay_plugins.items() if "desc" in pay_data },
        "policy": policy.data()
    })


@application.route('/pyrar/v1.0/zones', methods=['GET'])
def get_supported_zones():
    req = WebuiReq()
    return req.response(registry.tld_lib.return_zone_list())


@application.route('/pyrar/v1.0/hello', methods=['GET'])
def hello():
    req = WebuiReq()
    return req.response({"hello": "world"})


@application.route('/pyrar/v1.0/orders/details', methods=['GET'])
def orders_details():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    return load_orders_and_reply(req)


@application.route('/pyrar/v1.0/orders/cancel', methods=['POST'])
def orders_cancel():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    if req.post_js is None or "order_item_id" not in req.post_js or not isinstance(
            req.post_js["order_item_id"], int):
        return req.abort("No/invalid JSON posted")

    where = {"user_id": req.user_id, "order_item_id": int(req.post_js["order_item_id"])}
    ok, order_db = sql.sql_select_one("orders", where)
    if not ok:
        return req.abort(order_db)
    if len(order_db) <= 0:
        return req.abort("Order not found")

    event_db = {"event_type": "order/cancel"}
    dom_name = f"DOM-{order_db['domain_id']}"
    ok, dom_db = sql.sql_select_one("domains", {"domain_id": order_db["domain_id"], "user_id": req.user_id})
    if ok:
        event_db["domain_id"] = dom_db["domain_id"]
        dom_name = dom_db['name']

    event_db["notes"] = f"Cancel Order: {dom_name} order for {order_db['order_type']} for {order_db['num_years']}"

    ok = sql.sql_delete_one("orders", where)
    if not ok:
        return req.abort("Order not found")

    if order_db["order_type"] == "dom/create":
        sql.sql_delete_one("domains", {
            "domain_id": order_db["domain_id"],
            "user_id": req.user_id,
            "status_id": misc.STATUS_WAITING_PAYMENT
        })

    req.event(event_db)
    return load_orders_and_reply(req)


@application.route('/pyrar/v1.0/basket/submit', methods=['POST'])
def basket_submit():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    if req.post_js is None:
        return req.abort("No JSON posted")

    ok, reply = basket.webui_basket(req.post_js, req)
    if not ok:
        return req.abort(reply)

    req.user_data["failed_basket"] = [item for item in reply if "failed" in item]
    for order in req.user_data["failed_basket"]:
        for col in list(order):
            if col in ["prices", "order_db"]:
                del order[col]

    req.user_data["orders"] = [item["order_db"] for item in reply if "order_db" in item]
    return req.response(req.user_data)


@application.route('/pyrar/v1.0/payments/delete', methods=['POST'])
def payments_delete():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if not sql.has_data(req.post_js,["provider","provider_tag"]):
        return req.abort("Missing or invalid payment method data")
    req.post_js["user_id"] = req.user_id
    ok = sql.sql_delete_one("payments",req.post_js)
    if not ok:
        return req.abort("Failed to remove payment method")
    return req.response(True)


@application.route('/pyrar/v1.0/payments/validate', methods=['POST'])
def payments_validate():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if not sql.has_data(req.post_js,["provider","provider_tag","single_use","can_pull"]):
        return req.abort("Missing or invalid payment method data")

    if (plugin_func :=  pay_handler.run(req.post_js["provider"],"validate")) is None:
        return req.abort("Missing or invalid payment method data")

    req.post_js["user_id"] = req.user_id
    ok = plugin_func(req.post_js)
    if not ok:
        return req.abort("Failed validation")

    req.post_js["created_dt"] = None
    req.post_js["amended_dt"] = None
    ok, reply = sql.sql_insert("payments",req.post_js)
    if not ok:
        return req.abort("Adding payments data failed")

    return req.response(True)


@application.route('/pyrar/v1.0/payments/html', methods=['POST'])
def payments_html():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if req.post_js is None or "method" not in req.post_js or req.post_js["method"] not in pay_handler.pay_plugins:
        return req.abort("Missign or invalid payment method")
    if (plugin_func :=  pay_handler.run(req.post_js["method"],"html")) is None:
        return req.abort("Missign or invalid payment method")

    ok, reply = plugin_func(req.user_id)
    if not ok:
        return req.abort("Missign or invalid payment method")
    return req.response(reply)


@application.route('/pyrar/v1.0/payments/list', methods=['GET', 'POST'])
def payments_list():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    ok, reply = sql.sql_select("payments",{"user_id":req.user_id})
    if not ok:
        return req.abort("Failed to load payment data")
    return req.response(reply)


@application.route('/pyrar/v1.0/users/transactions', methods=['GET', 'POST'])
def users_transactions():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    limit = int(policy.policy("trans_per_page"))
    if req.post_js is not None and "limit" in req.post_js and isinstance(req.post_js["limit"],int):
        limit = int(req.post_js["limit"])
        if "skip" in req.post_js and isinstance(req.post_js["skip"],int):
            limit = f"{limit} OFFSET {int(req.post_js['skip'])}"

    ok, trans_db = sql.sql_select("transactions", {"user_id": req.user_id},
                                  limit=limit,
                                  order_by="acct_sequence_id desc")
    if not ok:
        return req.abort("Unexpected error loading transactions")
    req.user_data["transactions"] = trans_db
    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/domains', methods=['GET'])
def users_domains():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ret, doms_db = sql.sql_select("domains", {"user_id": req.user_id}, order_by="name")
    if ret is None:
        return req.abort("Failed to load domains")

    now = sql.now()
    for dom_db in doms_db:
        if dom_db["status_id"] == misc.LIVE_STATUS and dom_db["expiry_dt"] <= now:
            dom_db["status_id"] = misc.STATUS_EXPIRED
        dom_db["is_live"] = dom_db["status_id"] in misc.LIVE_STATUS

    req.user_data["domains"] = doms_db

    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/update', methods=['POST'])
def users_update():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    if req.post_js is None:
        return req.abort("No JSON posted")

    ret, user_data = users.update_user(req.user_id, req.post_js)
    if not ret:
        return req.abort(user_data)

    req.user_data["user"] = user_data

    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/close', methods=['POST'])
def users_close():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    if not users.check_password(req.user_id, req.post_js):
        return req.abort("Password match failed")

    ok = sql.sql_update_one(
        "users",
        "account_closed=1,email=concat(user_id,':',email),password=concat('CLOSED:',password),amended_dt=now()",
        {"user_id": req.user_id})

    if not ok:
        return req.abort("Close account failed")

    sql.sql_delete_one("session_keys", {"user_id": req.user_id})
    req.user_id = None
    req.sess_code = None

    return req.response("OK")


@application.route('/pyrar/v1.0/users/password', methods=['POST'])
def users_password():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    if not users.check_password(req.user_id, req.post_js):
        return req.abort("Password match failed")

    new_pass = passwd.crypt(req.post_js["new_password"])
    ok = sql.sql_update_one("users", {"password": new_pass, "amended_dt": None}, {"user_id": req.user_id})

    if not ok:
        return req.response("OK")

    return req.abort("Failed")


@application.route('/pyrar/v1.0/users/details', methods=['GET'])
def users_details():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ok, user_db = sql.sql_select_one("users", {"user_id": req.user_id})
    if not ok:
        return req.abort("Failed to load user account")

    req.user_data["user"] = user_db

    return load_orders_and_reply(req)


def load_orders_and_reply(req):
    ok, orders_db = sql.sql_select("orders", {"user_id": req.user_id})
    if not ok:
        return req.abort(orders_db)

    req.user_data["orders"] = orders_db
    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/login', methods=['POST'])
def users_login():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")

    ret, data = users.login(req.post_js, req.user_agent)
    if not ret or not data:
        return req.abort("Login failed")

    req.parse_user_data(ret, data)
    return req.response(data)


@application.route('/pyrar/v1.0/users/logout', methods=['GET'])
def users_logout():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    users.logout(req.sess_code, req.user_id, req.user_agent)

    req.sess_code = None
    req.user_id = None

    return req.response("logged-out")


@application.route('/pyrar/v1.0/send/verify', methods=['GET','POST'])
def send_verify():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if spool_email.spool("verify_email",[["users",{"user_id":req.user_id}]]):
        return req.response(True)
    return req.abort("Failed to send email verification")


@application.route('/pyrar/v1.0/users/verify', methods=['POST'])
def users_verify():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")

    if not sql.has_data(req.post_js,["user_id","hash"]) or not isinstance(req.post_js["user_id"],int) or len(req.post_js["hash"]) != 20:
        return req.abort("Invalid verification data")
    if users.verify_email(int(req.post_js["user_id"]),req.post_js["hash"]):
        return req.response(True)
    return req.abort("Email verification failed")


@application.route('/pyrar/v1.0/users/register', methods=['POST'])
def users_register():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")

    ret, val = users.register(req.post_js, req.user_agent)
    if not ret:
        return req.abort(val)

    debug("REGISTER " + str(val))

    user_id = val["user"]["user_id"]
    req.user_id = user_id
    req.sess_code = val["session"]
    req.base_event["user_id"] = user_id
    req.event({"notes": "User registered", "event_type": "new_user"})

    return req.response(val)


def pdns_action(func):
    req = WebuiReq()
    if req.post_js is None or not sql.has_data(req.post_js, "name") or not validate.is_valid_fqdn(req.post_js["name"]):
        return req.abort("No JSON posted or domain is missing")

    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ok, dom_db = sql.sql_select_one("domains", {"name": req.post_js["name"], "user_id": req.user_id})
    if not ok:
        return req.abort("Domain not found or not yours")

    return func(req, dom_db)


def pdns_get_data(req, dom_db):
    dom_name = dom_db["name"]
    if not pdns.zone_exists(dom_name):
        dns = pdns.create_zone(dom_name)
    else:
        dns = pdns.load_zone(dom_name)

    if dns and "dnssec" in dns and dns["dnssec"]:
        dns["keys"] = pdns.load_zone_keys(dom_name)
        dns["ds"] = find_best_ds(dns["keys"])

    return req.response({"domain": dom_db, "dns": dns})


def pdns_sign_zone(req, dom_db):
    key_data = pdns.sign_zone(dom_db["name"])
    if key_data is None:
        return req.abort("No DNSSEC Keys found")

    if dom_db["ns"] == policy.policy("dns_servers"):
        update_doms_ds(req, key_data, dom_db)

    return pdns_get_data(req, dom_db)


def pdns_unsign_zone(req, dom_db):
    if pdns.unsign_zone(dom_db["name"]) and dom_db["ns"] == policy.policy("dns_servers"):
        sql.sql_update_one("domains", {"ds": None}, {"domain_id": dom_db["domain_id"], "user_id": req.user_id})
        dom_db["ds"] = None
        domains.domain_backend_update(dom_db)
        sigprocs.signal_service("backend")
    return pdns_get_data(req, dom_db)


def update_doms_ds(req, key_data, dom_db):
    ds_rr = find_best_ds(key_data)
    dom_db["ds"] = ds_rr
    sql.sql_update_one("domains", {"ds": ds_rr}, {"domain_id": dom_db["domain_id"], "user_id": req.user_id})
    domains.domain_backend_update(dom_db)
    sigprocs.signal_service("backend")


def find_best_ds(key_data):
    for key in key_data:
        if "ds" in key:
            for ds_rr in key["ds"]:
                if ds_rr.find(" 2 ") >= 0:
                    return ds_rr


def pdns_drop_zone(req, dom_db):
    if pdns.delete_zone(dom_db["name"]):
        return req.response(True)
    return req.abort("Domain data failed to drop")


def check_rr_data(dom_db, add_rr):
    if "rr" not in add_rr:
        log("No `rr` property")
        return False

    for item in ["name", "type", "data", "ttl"]:
        if item not in add_rr["rr"]:
            log(f"{item} is missing")
            return False

    if not validate.is_valid_hostname(add_rr["rr"]["name"]):
        log("Invalid host name")
        return False
    if not validate.valid_rr_type(add_rr["rr"]["type"]):
        log(f"Invalid RR type")
        return False
    if not isinstance(add_rr["rr"]["ttl"], int):
        log(f"TTL is not integer")
        return False

    if len(add_rr["rr"]["name"]) > len(
            dom_db["name"]) and add_rr["rr"]["name"][-1 * len(dom_db["name"]) - 1:-1] != dom_db["name"]:
        log(f"Bad name suffix")
        return False

    return True


def pdns_update_rrs(req, dom_db):
    if not check_rr_data(dom_db, req.post_js):
        return req.abort("RR data missing or invalid")

    ok, reply = pdns.update_rrs(dom_db["name"], req.post_js["rr"])
    if not ok:
        return req.abort(reply)

    return req.response(True)


@application.route('/pyrar/v1.0/dns/update', methods=['POST'])
def domain_dns_update():
    return pdns_action(pdns_update_rrs)


@application.route('/pyrar/v1.0/dns/drop', methods=['POST'])
def domain_dns_drop():
    return pdns_action(pdns_drop_zone)


@application.route('/pyrar/v1.0/dns/unsign', methods=['POST'])
def domain_dns_unsign():
    return pdns_action(pdns_unsign_zone)


@application.route('/pyrar/v1.0/dns/sign', methods=['POST'])
def domain_dns_sign():
    return pdns_action(pdns_sign_zone)


@application.route('/pyrar/v1.0/dns/load', methods=['POST'])
def domain_dns_load():
    return pdns_action(pdns_get_data)


@application.route('/pyrar/v1.0/domain/gift', methods=['POST'])
def domain_gift():
    return run_user_domain_task(domains.webui_gift_domain, "Gift")


@application.route('/pyrar/v1.0/domain/update', methods=['POST'])
def domain_update():
    return run_user_domain_task(domains.webui_update_domain, "Update")


@application.route('/pyrar/v1.0/domain/authcode', methods=['POST'])
def domain_authcode():
    return run_user_domain_task(domains.webui_set_auth_code, "setAuth")


def run_user_domain_task(domain_function, func_name):
    req = WebuiReq()
    if req.post_js is None or not sql.has_data(req.post_js, "name"):
        return req.abort("No JSON posted or domain is missing")

    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ok, reply = domain_function(req, req.post_js)

    if not ok:
        return req.abort(reply)

    context = inspect.stack()[1]
    notes = context.function
    if func_name == "Gift":
        if "dest_email" not in req.post_js or not validate.is_valid_email(req.post_js["dest_email"]):
            return req.abort("Invalid recipient")
        notes = f"Domain gifted from {req.user_id} to {req.post_js['dest_email']}"

    req.event({"domain_id": req.post_js["domain_id"], "notes": notes, "event_type": context.function})
    if func_name == "Gift":
        req.event({
            "user_id": reply["new_user_id"],
            "domain_id": req.post_js["domain_id"],
            "notes": notes,
            "event_type": context.function
        })

    return req.response(reply)


def get_dom_data_items():
    num_years = 1
    qry_type = ["create", "renew"]
    post_js = flask.request.json

    if post_js is not None:
        dom = post_js["domain"]

        if not isinstance(dom, str) and not isinstance(dom, list):
            return None, "Unsupported data type for domain", None

        if "num_years" in post_js:
            num_years = int(post_js["num_years"])
        if "qry_type" in post_js:
            qry_type = post_js["qry_type"].split(",")
        return dom, num_years, qry_type

    data = None
    if flask.request.method == "POST":
        data = flask.request.form
    if flask.request.method == "GET":
        data = flask.request.args
    if data is None or len(data) <= 0:
        return None, "No data sent", None

    if (dom := data.get("domain")) is None:
        return None, "No domain sent", None

    if (yrs := data.get("num_years")) is not None:
        num_years = int(yrs)
    if (qry := data.get("qry_type")) is not None:
        qry_type = qry.split(",")

    return dom, num_years, qry_type


@application.route('/pyrar/v1.0/domain/check', methods=['POST', 'GET'])
def rest_domain_price():
    req = WebuiReq()

    dom, num_years, qry_type = get_dom_data_items()
    if dom is None:
        return req.abort(num_years)

    dom_obj = domains.DomainName(dom)

    if dom_obj.names is None:
        return req.abort(dom_obj.err if dom_obj.err is not None else "Invalid domain name")

    ok, reply = domains.get_domain_prices(dom_obj, num_years, qry_type, req.user_id)
    if ok:
        return req.response(reply)

    log(f"FAILED: {ok}:{reply}:{dom_obj.names}")
    return req.abort(reply)


if __name__ == "__main__":
    log_init(with_debug=True)
    application.run()
    domains.close_epp_sess()
