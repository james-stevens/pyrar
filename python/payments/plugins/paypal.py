#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json

from librar.policy import this_policy as policy
from librar.log import log, init as log_init
from librar import mysql as sql
from librar import misc
from librar import static
from librar import accounts
from mailer import spool_email

from payments import pay_handler
from payments import payfile

THIS_MODULE = "paypal"


def paypal_config():
    pay_conf = payfile.payment_file.data()
    if not isinstance(pay_conf, dict) or THIS_MODULE not in pay_conf:
        return None

    return_conf = {"desc": "PayPal"}
    payapl_conf = pay_conf[THIS_MODULE]
    paypal_mode = payapl_conf["mode"] if "mode" in payapl_conf else "live"
    if paypal_mode in payapl_conf and "client_id" in payapl_conf[paypal_mode]:
        return_conf["client_id"] = payapl_conf[paypal_mode]["client_id"]
    elif "client_id" in payapl_conf:
        return_conf["client_id"] = payapl_conf["client_id"]
    else:
        return None
    return return_conf


def paypal_startup():
    pay_conf = payfile.payment_file.data()
    if not isinstance(pay_conf, dict) or THIS_MODULE not in pay_conf:
        return None

    payapl_conf = pay_conf[THIS_MODULE]
    paypal_mode = payapl_conf["mode"] if "mode" in payapl_conf else "live"

    if paypal_mode in payapl_conf and "webhook" in payapl_conf[paypal_mode]:
        pay_handler.pay_webhooks[payapl_conf[paypal_mode]["webhook"]] = THIS_MODULE
    return True


class PayPalWebHook:
    def __init__(self, sent_json, filename):
        self.input = sent_json
        self.filename = filename
        self.currency = None
        self.amount = None
        self.email = None
        self.payer_id = None
        self.token = None
        self.user_id = None
        self.desc = None
        self.paypal_trans_id = None
        self.msg = None

    def err_exit(self, msg):
        self.error = msg
        log(msg)
        return False

    def check_data(self):
        if "resource" not in self.input or "purchase_units" not in self.input["resource"] or len(self.input["resource"]["purchase_units"]) != 1:
            return self.err_exit("ERROR: PayPal record does have one 'resource.purchase_units'")

        pay_unit = self.input["resource"]["purchase_units"][0]
        if "payments" not in pay_unit or "captures" not in pay_unit["payments"] or not isinstance(
                pay_unit["payments"]["captures"], list) or len(pay_unit["payments"]["captures"]) != 1:
            return self.err_exit("ERROR: PayPal 'amount' record missing or invalid")

        captured = pay_unit["payments"]["captures"][0]
        currency = policy.policy("currency")
        if "currency_code" not in captured["amount"] or captured["amount"]["currency_code"] != currency["iso"]:
            return self.err_exit(f"ERROR: PayPal currency missing or doesn't match '{currency['iso']}'")

        self.currency = captured["amount"]["currency_code"]

        if "value" not in captured["amount"]:
            return self.err_exit(f"ERROR: PayPal amount has no 'value' field")

        self.amount = misc.amt_from_float(captured["amount"]["value"])

        if "status" in captured and captured["status"] != "COMPLETED":
            return self.err_exit(f"ERROR: PayPal status '{captured['status']}' is not 'COMPLETED'")

        if "custom_id" in pay_unit:
            self.token = pay_unit["custom_id"]
        self.paypal_trans_id = self.input["id"] if "id" in self.input else self.token

        if "payer" in self.input:
            if "email_address" in self.input["payer"]:
                self.email = self.input["payer"]["email_address"]
            if "payer_id" in self.input["payer"]:
                self.payer_id = self.input["payer"]["payer_id"]

        self.desc = pay_unit["description"] if "description" in pay_unit else f"PayPal Credit"

        if self.token is None or self.email is None or self.payer_id is None:
            return self.err_exit(f"Failed to find all data items ({self.token},{self.email},{self.payer_id})")

        return True

    def try_match_user(self, prov_ext, token, single_use=False):
        where = {
            "provider": f"{THIS_MODULE}:{prov_ext}",
            "token": token,
            "token_type": static.PAY_TOKEN_SINGLE if single_use else static.PAY_TOKEN_VERIFIED
        }
        ok, pay_db = sql.sql_select_one("payments", where)
        if ok:
            self.user_id = pay_db["user_id"]
            if single_use:
                sql.sql_delete_one("payments", {"payment_id": pay_db["payment_id"]})
            return True
        return False

    def get_user_id(self):
        if self.token is not None and self.try_match_user("single", self.token, single_use=True):
            return True
        if self.email is not None and self.try_match_user("email", self.email):
            return True
        if self.payer_id is not None and self.try_match_user("payer_id", self.payer_id):
            return True
        self.msg = "Failed to get user identity"
        return False

    def store_one_identity(self, prov_ext, token):
        if self.user_id is None:
            return False
        pay_db = {
            "provider": f"{THIS_MODULE}:{prov_ext}",
            "token": token,
            "token_type": static.PAY_TOKEN_VERIFIED,
            "user_id": self.user_id,
            "created_dt": None,
            "amended_dt": None
        }
        return sql.sql_insert("payments", pay_db, ignore=True)

    def store_users_identity(self):
        if self.email is not None:
            self.store_one_identity("email", self.email)
        if self.payer_id is not None:
            self.store_one_identity("payer_id", self.payer_id)

    def credit_users_account(self):
        if self.user_id is None:
            return False, None
        ok, trans_id = accounts.apply_transaction(self.user_id, self.amount, f"PayPal: {self.desc}", as_admin=True)
        if ok:
            spool_email.spool("payment_done", [["users", {
                "user_id": self.user_id
            }], ["transactions", {
                "transaction_id": trans_id
            }], [None, {
                "provider": "PayPal",
                "paypal_trans_id": self.paypal_trans_id,
                "paypal_email": self.email
            }]])
            return True
        return False

    def event_log(self, notes):
        misc.event_log({
            "event_type": f"{THIS_MODULE}/payment",
            "user_id": self.user_id,
            "who_did_it": "paypal/webhook",
            "notes": notes,
            "filename": self.filename
        })

    def process_webhook(self):
        if not self.check_data():
            return False, self.msg
        if not self.get_user_id():
            self.event_log("Failed to match user to payment")
            return False, self.msg
        self.event_log("Successfully matched user to payment")
        self.store_users_identity()
        if not self.credit_users_account():
            return False, self.msg
        return True, True


def paypal_process_webhook(sent_data, filename):
    hook = PayPalWebHook(sent_data, filename)
    ok, reply = hook.process_webhook()
    if not ok:
        log(f"PayPal Processing Error: {reply}")
    return ok, reply


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "config": paypal_config,
    "startup": paypal_startup,
    "webhook": paypal_process_webhook,
})


def run_debug():
    log_init(with_debug=True)
    sql.connect("engine")
    with open("/opt/github/pyrar/tmp/paypal3.json", "r", encoding="utf-8") as fd:
        print(paypal_process_webhook(json.load(fd),"/opt/github/pyrar/tmp/paypal.json"))


if __name__ == "__main__":
    run_debug()
