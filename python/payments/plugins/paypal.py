#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json

from librar.policy import this_policy as policy
from librar.log import log, init as log_init
from librar import mysql as sql
from librar import misc
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
    if "webhook" in payapl_conf:
        pay_handler.pay_webhooks[payapl_conf["webhook"]] = THIS_MODULE
    return True


class PayPalWebHook:
    def __init__(self, sent_json):
        self.input = sent_json
        self.currency = None
        self.amount = None
        self.email = None
        self.payer_id = None
        self.provider_tag = None
        self.user_id = None
        self.pay_db = None
        self.desc = None
        self.paypal_trans_id = None
        self.msg = None

    def err_exit(self, msg):
        self.error = msg
        log(msg)
        return False

    def check_data(self):
        if len(self.input["purchase_units"]) != 1:
            return self.err_exit("ERROR: PayPal record does have one 'purchase_units'")

        pay_unit = self.input["purchase_units"][0]
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
            self.provider_tag = pay_unit["custom_id"]
        self.paypal_trans_id = self.input["id"] if "id" in self.input else self.provider_tag

        if "payer" in self.input:
            if "email_address" in self.input["payer"]:
                self.email = self.input["payer"]["email_address"]
            if "payer_id" in self.input["payer"]:
                self.payer_id = self.input["payer"]["payer_id"]

        self.desc = pay_unit["description"] if "description" in pay_unit else f"PayPal Credit"

        return self.provider_tag is not None or self.email is not None or self.payer_id is not None

    def try_this_where(self, prov_ext, provider_tag, delete_after=False):
        where = {"provider": f"{THIS_MODULE}:{prov_ext}", "provider_tag": provider_tag}
        ok, self.pay_db = sql.sql_select_one("payments", where)
        if ok:
            self.user_id = self.pay_db["user_id"]
            if delete_after:
                sql.sql_delete_one("payments", where)
            return True
        return False

    def get_user_id(self):
        if self.provider_tag is not None and self.try_this_where("single", self.provider_tag, delete_after=True):
            return True
        if self.email is not None and self.try_this_where("email", self.email):
            return True
        if self.payer_id is not None and self.try_this_where("payer_id", self.payer_id):
            return True
        self.msg = "Failed to get user identity"
        return False

    def store_one_identity(self, prov_ext, provider_tag):
        if self.user_id is None:
            return False
        pay_db = {
            "provider": f"{THIS_MODULE}:{prov_ext}",
            "provider_tag": provider_tag,
            "single_use": False,
            "user_id": self.user_id,
            "can_pull": 0,
            "verified": True,
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


def paypal_process_webhook(sent_data):
    hook = PayPalWebHook(sent_data)
    if not hook.check_data():
        return False, hook.msg
    if not hook.get_user_id():
        return False, hook.msg
    hook.store_users_identity()
    if not hook.credit_users_account():
        return False, hook.msg
    return True, True


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "config": paypal_config,
    "startup": paypal_startup,
    "webhook": paypal_process_webhook,
})


def run_debug():
    log_init(with_debug=True)
    sql.connect("engine")
    with open("/opt/github/pyrar/tmp/paypal.json", "r", encoding="utf-8") as fd:
        hook = PayPalWebHook(json.load(fd))
    print("check_data", hook.check_data())
    print("amount", hook.amount)
    print("currency", hook.currency)
    print("prov_tag", hook.provider_tag)
    print("desc", hook.desc)
    print("email", hook.email)
    print("payer_id", hook.payer_id)
    ret = hook.get_user_id()
    print("get_user_id", ret)
    print("user_id", hook.user_id)
    if ret:
        hook.store_users_identity()
        hook.credit_users_account()


if __name__ == "__main__":
    run_debug()
