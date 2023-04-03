#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" module to run the rest/api for user's site web/ui """

import inspect
import flask

from librar import registry, validate, passwd, pdns, common_ui, static, misc, domobj, sigprocs, hashstr
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy
from librar.mysql import sql_server as sql
from mailer import spool_email
from webui import users, domains, basket
from payments import libpay, pay_handler, payfuncs
from actions import make_actions

WANT_REFERRER_CHECK = True

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

log_init("logging_webui")
sql.connect("webui")
application = flask.Flask("EPP Registrar")
registry.start_up()
pdns.start_up()
libpay.startup()

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
        """ set up session properties """
        if not logged_in or "session" not in check_sess_data:
            return

        self.user_data = check_sess_data
        self.sess_code = check_sess_data["session"]
        self.user_id = check_sess_data['user_id']
        debug(f"Logged in as {self.user_id}")

    def set_base_event(self):
        """ set up properties common to all events, for logging events """
        ip_addr = flask.request.remote_addr
        if "x-forwaded-for" in self.headers:
            ip_addr = self.headers["x-forwaded-for"]
        return {"from_where": ip_addr, "user_id": self.user_id, "who_did_it": "webui"}

    def abort(self, data):
        """ return error code to caller """
        return self.response({"error": data}, HTML_CODE_ERR)

    def secure_user_data(self):
        """ remove data columns the user shouldnt see """
        if self.user_data is None:
            return
        for table, remove_cols in REMOVE_TO_SECURE.items():
            if table in self.user_data and isinstance(self.user_data[table], dict):
                for column in remove_cols:
                    if column in self.user_data[table]:
                        del self.user_data[table][column]

    def send_user_data(self):
        check_messages(self, self.user_data)
        return self.response(self.user_data)

    def response(self, data, code=HTML_CODE_OK):
        """ return OK response & data to caller """
        self.secure_user_data()
        resp = flask.make_response(flask.jsonify(data), code)
        resp.charset = 'utf-8'
        if self.sess_code is not None:
            resp.headers[SESSION_TAG] = self.sess_code
        return resp

    def event(self, data):
        """ log an event """
        context = inspect.stack()[1]
        data["program"] = context.filename.split("/")[-1]
        data["function"] = context.function
        data["line_num"] = context.lineno
        data["when_dt"] = None
        for item, evt_data in self.base_event.items():
            if item not in data:
                data[item] = evt_data
        sql.sql_insert("events", data)


@application.before_request
def before_request():
    if (flask.request.path.find("/pyrar/v1.0/hookid/") == 0 or flask.request.path.find("/pyrar/v1.0/webhook/") == 0
            or not WANT_REFERRER_CHECK):
        return None

    strict_referrer = policy.policy("strict_referrer")
    if strict_referrer is not None and not strict_referrer:
        return None

    allowable_referrer = policy.policy("allowable_referrer")
    if allowable_referrer is not None and isinstance(allowable_referrer, (dict, list)):
        if flask.request.referrer in allowable_referrer:
            return None
    elif flask.request.referrer == policy.policy("website_name"):
        return None

    return flask.make_response(flask.jsonify({"error": "Website continuity error"}), HTML_CODE_ERR)


@application.route('/pyrar/v1.0/config', methods=['GET'])
def get_config():
    req = WebuiReq()
    return req.response(common_ui.ui_config())


@application.route('/pyrar/v1.0/zones', methods=['GET'])
def get_supported_zones():
    req = WebuiReq()
    return req.response(registry.tld_lib.return_zone_list())


@application.route('/pyrar/v1.0/hello', methods=['GET'])
def hello():
    req = WebuiReq()
    return req.response({"hello": "world"})


def generic_get_data():
    if flask.request.json:
        return flask.request.json
    if flask.request.method == "POST":
        return dict(flask.request.form)
    if flask.request.method == "GET":
        return flask.request.args
    return None


@application.route('/pyrar/v1.0/hookid/<webhook>/<trans_id>/', methods=['GET', 'POST'])
def catch_hookid(webhook, trans_id):
    return run_webhook(WebuiReq(), webhook, trans_id)


@application.route('/pyrar/v1.0/webhook/<webhook>/', methods=['GET', 'POST'])
def catch_webhook(webhook):
    return run_webhook(WebuiReq(), webhook)


def run_webhook(req, webhook, trans_id=None):
    if webhook is None or webhook not in pay_handler.pay_webhooks:
        return req.abort(f"Webhook not recognised - '{webhook}'")

    if trans_id is not None:
        req.headers["hook_trans_id"] = trans_id

    ok, reply = libpay.process_webhook(req.headers, pay_handler.pay_webhooks[webhook], generic_get_data())
    if not ok:
        return req.abort(reply)
    return req.response(reply)


@application.route('/pyrar/v1.0/messages/read', methods=['GET'])
def api_messages_read():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    ok, reply = sql.sql_select("messages", {"user_id": req.user_id}, order_by="message_id desc", limit=75)
    if not ok:
        return req.abort(reply)
    sql.sql_update("messages", {"is_read": True}, {"user_id": req.user_id, "is_read": False})
    return req.response(reply)


def check_messages(req, data):
    data["messages"] = sql.sql_exists("messages", {"user_id": req.user_id, "is_read": False})


@application.route('/pyrar/v1.0/messages/check', methods=['GET'])
def api_messages_check():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    return req.response(sql.sql_exists("messages", {"user_id": req.user_id, "is_read": False}))


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

    if req.post_js is None or "order_item_id" not in req.post_js or not isinstance(req.post_js["order_item_id"], int):
        return req.abort("No/invalid JSON posted")

    where = {"user_id": req.user_id, "order_item_id": int(req.post_js["order_item_id"])}

    ok, order_db = sql.sql_select_one("orders", where)
    if not ok:
        return req.abort("Order could not be found")

    dom_db = None
    event_db = {"event_type": "order/cancel"}
    dom_name = f"DOM-{order_db['domain_id']}"
    ok, reply = sql.sql_select_one("domains", {"domain_id": order_db["domain_id"], "user_id": req.user_id})
    if ok and len(reply):
        dom_db = reply
        event_db["domain_id"] = dom_db["domain_id"]
        dom_name = dom_db['name']

    event_db["notes"] = f"Cancel Order: {dom_name} order for {order_db['order_type']} for {order_db['num_years']}"

    if not sql.sql_delete_one("orders", where):
        return req.abort("Order not found")

    if order_db["order_type"] == "dom/create":
        sql.sql_delete_one("domains", {
            "domain_id": order_db["domain_id"],
            "user_id": req.user_id,
            "status_id": static.STATUS_WAITING_PAYMENT
        })
        sql.sql_delete("actions", {"domain_id": order_db["domain_id"]})
        if dom_db:
            pdns.delete_zone(dom_db["name"])
    else:
        ok, dom_db = sql.sql_select_one("domains", {"domain_id": order_db["domain_id"]})
        if ok and len(dom_db) > 0:
            make_actions.recreate(dom_db)

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
    return req.send_user_data()


@application.route('/pyrar/v1.0/payments/single', methods=['DELETE'])
def payments_delete():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if not misc.has_data(req.post_js, ["provider", "token"]):
        return req.abort("Missing or invalid payment method data")

    provider = req.post_js["provider"]
    if provider.find(":") > 0:
        provider = provider.split(":")[0]
    if provider not in pay_handler.pay_plugins:
        return req.abort(f"Invalid payment provider '{req.post_js['provider']}'")

    pay_db = {
        "provider": req.post_js["provider"],
        "token": req.post_js["token"],
        "user_can_delete": True,
        "user_id": req.user_id
    }

    if not sql.sql_delete_one("payments", pay_db):
        return req.abort("Failed to remove payment method")
    return req.response(True)


@application.route('/pyrar/v1.0/payments/submitted', methods=['POST'])
def payments_update_status():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if not misc.has_data(req.post_js, "amount") or not isinstance(req.post_js["amount"], int):
        return req.abort("Missing or invalid payment method data")
    payfuncs.set_orders_status(req.user_id, req.post_js["amount"], "submitted")
    return req.response(True)


@application.route('/pyrar/v1.0/payments/single', methods=['POST'])
def payments_single():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if not misc.has_data(req.post_js, ["provider","amount","description"]):
        return req.abort("Missing or invalid payment method data")

    provider = req.post_js["provider"]
    pay_conf = payfuncs.payment_file.data()
    if provider not in pay_conf or provider not in pay_handler.pay_plugins:
        return req.abort(f"Unsupported provider - {provider}")

    if (func := pay_handler.run(provider, "single")) is None:
        return req.abort("Unsupported function 'single' for provider - {provider}")

    ok, reply = func(req.user_id,req.post_js["description"],req.post_js["amount"])
    return req.abort(reply) if not ok else req.response(reply)


@application.route('/pyrar/v1.0/payments/list', methods=['GET', 'POST'])
def payments_list():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    ok, reply = sql.sql_select("payments", {"user_id": req.user_id, "user_can_delete": True})
    if not ok and reply is None:
        return req.abort("Failed to load payment data")

    return req.response(reply)


@application.route('/pyrar/v1.0/users/transactions', methods=['GET', 'POST'])
def users_transactions():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    limit = int(policy.policy("trans_per_page"))
    if req.post_js is not None and "limit" in req.post_js and isinstance(req.post_js["limit"], int):
        limit = int(req.post_js["limit"])
        if "skip" in req.post_js and isinstance(req.post_js["skip"], int):
            limit = f"{limit} OFFSET {int(req.post_js['skip'])}"

    ok, trans_db = sql.sql_select("transactions", {"user_id": req.user_id},
                                  limit=limit,
                                  order_by="acct_sequence_id desc")
    if not ok and trans_db is None:
        return req.abort("Unexpected error loading transactions")

    req.user_data["transactions"] = trans_db
    return req.send_user_data()


@application.route('/pyrar/v1.0/domain/transfer', methods=['POST'])
def domain_transfer():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    if not misc.has_data(req.post_js, ["name", "authcode"]) or not validate.is_valid_fqdn(req.post_js["name"]):
        return req.abort("Missing or invalid data")

    ok, reply = domains.domain_transfer(req)
    if not ok:
        return req.abort(reply)
    return req.response(reply)


def add_domain_extras(dom, dom_db):
    dom_db["registry"] = dom.registry["name"]
    dom_db["locks"] = dom.locks
    dom_db["is_live"] = dom_db["status_id"] in static.IS_LIVE_STATUS
    dom_db["can_transfer"] = (dom_db["created_dt"] < dom.transfer_stop)


@application.route('/pyrar/v1.0/users/domains', methods=['GET'])
def users_domains():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ok, reply = sql.sql_select("domains", {"user_id": req.user_id}, order_by="name")
    if not ok:
        if reply is None:
            return req.abort("Failed to load domains")
        return req.response({})

    for dom_db in reply:
        dom = domobj.Domain()
        dom.set_name(dom_db["name"])
        add_domain_extras(dom, dom_db)

    req.user_data["domains"] = reply
    return req.send_user_data()


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
    return req.send_user_data()


@application.route('/pyrar/v1.0/users/close', methods=['POST'])
def users_close():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ok, user_db = sql.sql_select_one("users", {"user_id": req.user_id})
    if not ok:
        return req.abort("User record not found")

    if not users.check_password(req.user_id, req.post_js):
        return req.abort("Password match failed")

    where = {
        "account_closed": 1,
        "email": f"{req.user_id}:{user_db['email']}",
        "password": f"CLOSED:{user_db['password']}",
        "amended_dt": None
    }
    if not sql.sql_update_one("users", where, {"user_id": req.user_id}):
        return req.abort("Close account failed")

    sql.sql_delete_one("session_keys", {"user_id": req.user_id})
    sql.sql_delete("orders", {"user_id": req.user_id})
    sql.sql_delete("payments", {"user_id": req.user_id})
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
    if not sql.sql_update_one("users", {"password": new_pass, "amended_dt": None}, {"user_id": req.user_id}):
        return req.abort("Failed")

    spool_email.spool("password_changed", [["users", {"user_id": req.user_id}]])

    return req.response("OK")


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
    if not ok and orders_db is None:
        return req.abort("Orders failed to load")

    req.user_data["orders"] = orders_db
    return req.send_user_data()


@application.route('/pyrar/v1.0/users/login', methods=['POST'])
def users_login():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")

    ret, data = users.login(req.post_js, req.user_agent)
    if not ret or not data:
        return req.abort("Login failed")

    req.parse_user_data(ret, data)
    check_messages(req, data)

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


@application.route('/pyrar/v1.0/email/sendverify', methods=['GET', 'POST'])
def send_verify():
    req = WebuiReq()
    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)
    if spool_email.spool("verify_email", [["users", {"user_id": req.user_id}]]):
        return req.response(True)
    return req.abort("Failed to send email verification")


@application.route('/pyrar/v1.0/email/verify', methods=['POST'])
def users_verify():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")

    if not misc.has_data(req.post_js, ["user_id", "hash"]) or not isinstance(req.post_js["user_id"],
                                                                             int) or len(req.post_js["hash"]) != 20:
        return req.abort("Invalid verification data")
    if users.verify_email(int(req.post_js["user_id"]), req.post_js["hash"]):
        return req.response(True)
    return req.abort("Email verification failed")


@application.route('/pyrar/v1.0/password/request', methods=['POST'])
def request_reset_password():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")
    if not misc.has_data(req.post_js, ["pin", "email"]):
        return req.abort("Missing data")
    if not validate.is_valid_pin(req.post_js["pin"]) or not validate.is_valid_email(req.post_js["email"]):
        return req.abort("Invalid data")
    users.request_password_reset(req)
    return req.response(True)


@application.route('/pyrar/v1.0/password/reset', methods=['POST'])
def users_reset_password():
    req = WebuiReq()
    if req.post_js is None:
        return req.abort("No JSON posted")
    if not misc.has_data(req.post_js, ["pin", "code", "password", "confirm"]):
        return req.abort("Missing data")
    if req.post_js["password"] != req.post_js["confirm"] or len(
            req.post_js["code"]) != 30 or not validate.is_valid_pin(req.post_js["pin"]):
        return req.abort("Invalid data")

    if not users.reset_users_password(req):
        return req.abort("Password update failed")

    return req.response(True)


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


def pdns_action(func, action):
    req = WebuiReq()
    if req.post_js is None or not misc.has_data(req.post_js, "name"):
        return req.abort("No JSON posted or domain is missing")

    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    dom = domobj.Domain()
    ok, reply = dom.set_name(req.post_js["name"])

    if not ok:
        return req.abort(reply)

    dom.load_record(req.user_id)
    if dom.dom_db is None:
        return req.abort("Domain not found or not yours")

    add_domain_extras(dom, dom.dom_db)

    req.event({
        "domain_id": dom.dom_db["domain_id"],
        "notes": f"PDNS: calling '{action}' on '{dom.dom_db['name']}'",
        "event_type": action
    })
    return func(req, dom.dom_db)


def pdns_get_data(req, dom_db):
    dom_name = dom_db["name"]
    pdns.create_zone(dom_name, ensure_zone=True)
    dns = pdns.load_zone(dom_name)

    if dns and "dnssec" in dns and dns["dnssec"]:
        dns["keys"] = pdns.load_zone_keys(dom_name)
        dns["ds"] = pdns.find_best_ds(dns["keys"])

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
    ds_rr = pdns.find_best_ds(key_data)
    dom_db["ds"] = ds_rr
    sql.sql_update_one("domains", {"ds": ds_rr}, {"domain_id": dom_db["domain_id"], "user_id": req.user_id})
    domains.domain_backend_update(dom_db)
    sigprocs.signal_service("backend")


def pdns_drop_zone(req, dom_db):
    if pdns.delete_zone(dom_db["name"]):
        return req.response(True)
    return req.abort("Domain data failed to drop")


def check_rr_data(dom_db, add_rr):
    """ Validate an rr-set sent by user """
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
        log("Invalid RR type")
        return False
    if not isinstance(add_rr["rr"]["ttl"], int):
        log("TTL is not integer")
        return False

    if len(add_rr["rr"]["name"]) > len(
            dom_db["name"]) and add_rr["rr"]["name"][-1 * len(dom_db["name"]) - 1:-1] != dom_db["name"]:
        log("Bad name suffix")
        return False

    return True


def pdns_update_rrs(req, dom_db):
    """ complete task of updating rr-set """
    if not check_rr_data(dom_db, req.post_js):
        return req.abort("RR data missing or invalid")

    ok, reply = pdns.update_rrs(dom_db["name"], req.post_js["rr"])
    if not ok:
        return req.abort(reply)

    return req.response(True)


@application.route('/pyrar/v1.0/dns/tlsa', methods=['POST'])
def make_tlsa():
    req = WebuiReq()
    if req.post_js is None or not misc.has_data(req.post_js, ["name", "fqdn", "o", "ou", "l", "st", "c"]):
        return req.abort("No JSON posted or data is missing")

    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    for item in ["o", "ou", "l", "st", "c"]:
        if not validate.is_valid_display_name(req.post_js[item]):
            return req.abort("Invalid certificate information")
    if not validate.is_valid_fqdn(req.post_js["name"]) or not validate.is_valid_hostname(req.post_js["fqdn"]):
        return req.abort("Invalid certificate information")

    ok, pem = domains.webui_add_tlsa_record(req)
    if not ok:
        return req.abort(pem)

    return req.response(pem)


@application.route('/pyrar/v1.0/dns/update', methods=['POST'])
def domain_dns_update():
    """ Update an RR-set in P/DNS """
    return pdns_action(pdns_update_rrs, "pdns/update")


@application.route('/pyrar/v1.0/dns/drop', methods=['POST'])
def domain_dns_drop():
    """ Drop a domain & all its data in P/DNS """
    return pdns_action(pdns_drop_zone, "pdns/drop")


@application.route('/pyrar/v1.0/dns/unsign', methods=['POST'])
def domain_dns_unsign():
    """ Remove DNSSEC from a domain in P/DNS """
    return pdns_action(pdns_unsign_zone, "pdns/unsign")


@application.route('/pyrar/v1.0/dns/sign', methods=['POST'])
def domain_dns_sign():
    """ Sign a domain in P/DNS """
    return pdns_action(pdns_sign_zone, "pdns/sign")


@application.route('/pyrar/v1.0/dns/load', methods=['POST'])
def domain_dns_load():
    """ load domain's DNS data from P/DNS """
    return pdns_action(pdns_get_data, "pdns/load")


@application.route('/pyrar/v1.0/domain/gift', methods=['POST'])
def domain_gift():
    """ gift a domain to another user """
    return run_user_domain_task(domains.webui_gift_domain, "Gift")


@application.route('/pyrar/v1.0/domain/flags', methods=['POST'])
def domain_flags():
    """ update domain flags """
    return run_user_domain_task(domains.webui_update_domains_flags, "Flags")


@application.route('/pyrar/v1.0/domain/update', methods=['POST'])
def domain_update():
    """ update domain details """
    return run_user_domain_task(domains.webui_update_domain, "Update")


@application.route('/pyrar/v1.0/domain/authcode', methods=['POST'])
def domain_authcode():
    """ set domain authcode """
    return run_user_domain_task(domains.webui_set_authcode, "setAuth")


def run_user_domain_task(domain_function, func_name):
    """ start a {domain_function} & complete it by running {func_name}() """
    req = WebuiReq()
    if req.post_js is None or not misc.has_data(req.post_js, "name"):
        return req.abort("No JSON posted or domain is missing")

    if not req.is_logged_in:
        return req.abort(NOT_LOGGED_IN)

    ok, reply = domain_function(req)

    if not ok:
        return req.abort(reply)

    context = inspect.stack()[1]
    notes = f"Domain {func_name}: {context.function}"

    if func_name == "Gift":
        notes = f"Domain gifted from {req.user_id} to {req.post_js['dest_email']}"
        req.event({
            "user_id": reply["new_user_id"],
            "domain_id": req.post_js["domain_id"],
            "notes": notes,
            "event_type": context.function
        })

    req.event({"domain_id": req.post_js["domain_id"], "notes": notes, "event_type": context.function})
    return req.response(reply)


def get_price_check_properties(post_js):
    """ read domain check sent by the user, supporting GET/POST & JSON """
    num_years = 1
    qry_type = ["create", "renew"]

    if post_js is not None:
        if "domain" not in post_js:
            return None, "Missing domain", None

        dom = post_js["domain"]

        if not isinstance(dom, str) and not isinstance(dom, list):
            return None, "Unsupported data type for domain", None

        if "num_years" in post_js:
            num_years = int(post_js["num_years"])
        if "qry_type" in post_js:
            qry_type = post_js["qry_type"].split(",")
        return dom, num_years, qry_type

    data = generic_get_data()

    if data is None or len(data) <= 0:
        return None, "No data sent", None

    if (dom := data.get("domain")) is None:
        return None, "No domain sent", None

    if (yrs := data.get("num_years")) is not None:
        num_years = int(yrs)
    if (qry := data.get("qry_type")) is not None:
        qry_type = qry.split(",")

    if not validate.valid_domain_actions(qry_type):
        return None, "Imvalid actions", None

    return dom, num_years, qry_type


@application.route('/pyrar/v1.0/domain/check', methods=['POST', 'GET'])
def rest_domain_price():
    """ check the price of a domain or list of domains """
    req = WebuiReq()
    dom, num_years, qry_type = get_price_check_properties(req.post_js)
    if dom is None:
        return req.abort(num_years)

    domlist = domobj.DomainList()
    if not (reply := domlist.set_list(dom))[0]:
        return req.abort(reply[1] if reply[1] is not None else "Invalid domain name")

    ok, reply = domains.get_domain_prices(domlist, num_years, qry_type, req.user_id)
    if ok:
        return req.response(reply)

    return req.abort(reply)


def main():
    global WANT_REFERRER_CHECK
    log_init(with_debug=True)
    WANT_REFERRER_CHECK = False
    application.run()


if __name__ == "__main__":
    main()
