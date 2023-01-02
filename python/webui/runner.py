#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import inspect
import flask

from librar import registry
from librar import misc
from librar import validate
from librar import passwd
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy
from librar import mysql as sql
from webui import users
from webui import domains
from webui import basket

HTML_CODE_ERR = 499
HTML_CODE_OK = 200

NOT_LOGGED_IN = "Not logged in or login timed-out"

SESSION_TAG = "X-Session-Code"
SESSION_TAG_LOWER = SESSION_TAG.lower()

# remove these columns before transmitting to user
REMOVE_TO_SECURE = {
    "user": ["password", "two_fa", "password_reset"],
    "orders": ["price_charged","currency_charged"],
    "transactions": [ "sales_item_id"]
    }

log_init(policy.policy("facility_python_code"), with_logging=policy.policy("log_python_code"))
sql.connect("webui")
application = flask.Flask("EPP Registrar")
registry.start_up()

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
            if table in self.user_data and isinstance(self.user_data[table],dict):
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
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    return load_orders_and_reply(req)


@application.route('/pyrar/v1.0/orders/cancel', methods=['POST'])
def orders_cancel():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if flask.request.json is None or "order_item_id" not in flask.request.json:
        return req.abort("No/invalid JSON posted")

    where = {"user_id": req.user_id, "order_item_id": flask.request.json["order_item_id"]}
    ok, order_db = sql.sql_select_one("orders", where)
    if not ok:
        return req.abort(order_db)
    if len(order_db) <= 0:
        return req.abort("Order not found")

    ok = sql.sql_delete_one("orders", where)
    if not ok:
        return req.abort("Order not found")

    if order_db["order_type"] == "dom/create":
        sql.sql_delete_one("domains", {
            "domain_id": order_db["domain_id"],
            "user_id": req.user_id,
            "status_id": misc.STATUS_WAITING_PAYMENT
        })

    return load_orders_and_reply(req)


@application.route('/pyrar/v1.0/basket/submit', methods=['POST'])
def basket_submit():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if flask.request.json is None:
        return req.abort("No JSON posted")

    ok, reply = basket.webui_basket(flask.request.json, req.user_id)
    if not ok:
        return req.abort(reply)

    req.user_data["failed_basket"] = [ item for item in reply if "failed" in item ]
    for order in req.user_data["failed_basket"]:
        for col in list(order):
            if col in ["prices","order_db"]:
                del order[col]

    req.user_data["orders"] = [item["order_db"] for item in reply if "order_db" in item]
    return req.response(req.user_data)


@application.route('/pyrar/v1.0/users/transactions', methods=['GET', 'POST'])
def users_transactions():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if flask.request.json is None:
        limit = policy.policy("trans_per_page")
    else:
        if "limit" in flask.request.json:
            limit = flask.request.json["limit"]
            if "skip" in flask.request.json:
                limit = f"{limit} OFFSET {flask.request.json['skip']}"

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
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    ret, doms_db = sql.sql_select("domains", {"user_id": req.user_id}, order_by="name")
    if ret is None:
        return req.abort("Failed to load domains")

    now = sql.now()
    for dom_db in doms_db:
        if dom_db["status_id"] ==misc.LIVE_STATUS and dom_db["expiry_dt"] <= now:
            dom_db["status_id"] = misc.STATUS_EXPIRED

        if dom_db["status_id"] in misc.DOMAIN_STATUS:
            dom_db["status_desc"] = misc.DOMAIN_STATUS[dom_db["status_id"]]

        dom_db["is_live"] = dom_db["status_id"] in misc.LIVE_STATUS

    req.user_data["domains"] = doms_db

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
    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    if not users.check_password(req.user_id, flask.request.json):
        return req.abort("Password match failed")

    new_pass = passwd.crypt(flask.request.json["new_password"])
    ok = sql.sql_update_one("users", {"password": new_pass, "amended_dt": None}, {"user_id": req.user_id})

    if not ok:
        return req.response("OK")

    return req.abort("Failed")


@application.route('/pyrar/v1.0/users/details', methods=['GET'])
def users_details():
    req = WebuiReq()
    if req.user_id is None or req.sess_code is None:
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

    debug("REGISTER " + str(val))

    user_id = val["user"]["user_id"]
    req.user_id = user_id
    req.sess_code = val["session"]
    req.base_event["user_id"] = user_id
    req.event({"notes": "User registered", "event_type": "new_user"})

    return req.response(val)


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
    if flask.request.json is None or not sql.has_data(flask.request.json, "name"):
        return req.abort("No JSON posted or domain is missing")

    if req.user_id is None or req.sess_code is None:
        return req.abort(NOT_LOGGED_IN)

    ok, reply = domain_function(req, flask.request.json)

    if not ok:
        return req.abort(reply)

    context = inspect.stack()[1]
    notes = context.function
    if "dest_email" in flask.request.json:
        notes = f"Domain gifted from {req.user_id} to {flask.request.json['dest_email']}"

    req.event({"domain_id": flask.request.json["domain_id"], "notes": notes, "event_type": context.function})
    if func_name == "Gift":
        req.event({
            "user_id": reply["new_user_id"],
            "domain_id": flask.request.json["domain_id"],
            "notes": notes,
            "event_type": context.function
        })

    return req.response(reply)


def get_dom_data_items():
    num_years = 1
    qry_type = ["create", "renew"]

    if flask.request.json is not None:
        dom = flask.request.json["domain"]
        if not isinstance(dom, str) and not isinstance(dom, list):
            return None, "Unsupported data type for domain", None

        if "num_years" in flask.request.json:
            num_years = int(flask.request.json["num_years"])
        if "qry_type" in flask.request.json:
            qry_type = flask.request.json["qry_type"].split(",")
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

    log("FAILED:" + str(ok) + ":" + str(reply) + ":" + str(dom_obj.names))
    return req.abort(reply)


if __name__ == "__main__":
    log_init(with_debug=True)
    application.run()
    domains.close_epp_sess()
