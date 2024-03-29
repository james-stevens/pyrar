#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json

from librar.policy import this_policy as policy
from librar.log import log, init as log_init
from librar import misc, messages, static, accounts, mysql, hashstr
from librar.mysql import sql_server as sql
from mailer import spool_email

from payments import pay_handler
from payments import payfuncs

THIS_MODULE = "paypal"


def my_config():
    pay_conf = payfuncs.payment_file.data()
    if not isinstance(pay_conf, dict) or THIS_MODULE not in pay_conf:
        return None

    return_conf = {"desc": "Pay by PayPal"}
    my_conf = pay_conf[THIS_MODULE]
    my_mode = my_conf["mode"] if "mode" in my_conf else "live"
    if my_mode == "test":
        return_conf["desc"] = "Pay by PayPal SandBox"
    if my_mode in my_conf and "client_id" in my_conf[my_mode]:
        return_conf["client_id"] = my_conf[my_mode]["client_id"]
    elif "client_id" in my_conf:
        return_conf["client_id"] = my_conf["client_id"]
    else:
        return None
    return return_conf


def startup():
    return True


class PayPalWebHook:
    def __init__(self, webhook_data, sent_json, filename):
        self.input = sent_json
        self.webhook_data = webhook_data
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
        self.msg = msg
        log(f"PayPal Err: {msg}")
        return False

    def read_checkout_order(self):
        resource = self.input["resource"]
        if "payer" in resource:
            payer = resource["payer"]
            self.email = payer["email_address"] if "email_address" in payer else None
            self.payer_id = payer["payer_id"] if "payer_id" in payer else None

        pay_unit = resource["purchase_units"][0]
        self.token = pay_unit["custom_id"] if "custom_id" in pay_unit else None
        if "amount" in pay_unit:
            amt = pay_unit["amount"]
            self.amount = misc.amt_from_float(amt["value"]) if "value" in amt else None
            self.currency = amt["currency_code"] if "currency_code" in amt else None

        return self.email is not None and self.payer_id is not None

    def try_match_user(self, prov_ext, token, token_types, with_delete=False):
        where = {"provider": f"{THIS_MODULE}:{prov_ext}", "token": token, "token_type": token_types}
        ok, pay_db = sql.sql_select_one("payments", where)
        if ok:
            self.user_id = pay_db["user_id"]
            if with_delete:
                sql.sql_delete_one("payments", {"payment_id": pay_db["payment_id"]})
            return True
        return False

    def get_user_id(self, token_types, with_delete):
        return self.token is not None and self.try_match_user("single", self.token, token_types, with_delete)

    def store_one_identity(self, prov_ext, token):
        if self.user_id is None:
            return False
        pay_db = {
            "provider": f"{THIS_MODULE}:{prov_ext}",
            "token": token,
            "token_type": static.PAY_TOKEN_VERIFIED,
            "user_can_delete": True,
            "user_id": self.user_id
        }
        return sql.sql_insert("payments", pay_db, ignore=True)

    def store_users_identity(self):
        if self.email is not None:
            self.store_one_identity("email", self.email)
        if self.payer_id is not None:
            self.store_one_identity("payer_id", self.payer_id)

    def credit_users_account(self):
        if self.user_id is None:
            return self.err_exit("credit_users_account: user_id is missing")
        ok, trans_id = accounts.apply_transaction(self.user_id, self.amount, f"PayPal: {self.desc}", as_admin=True)
        if ok:
            spool_email.spool("payment_done", [["users", {
                "user_id": self.user_id
            }], ["transactions", {
                "transaction_id": trans_id
            }], [None, {
                "provider": "PayPal",
                "paypal_trans_id": self.paypal_trans_id
            }]])
            return True
        return False

    def interesting_webhook(self):
        if "event_type" in self.input and self.input["event_type"] in [
                "CHECKOUT.ORDER.APPROVED", "PAYMENT.CAPTURE.COMPLETED"
        ]:
            return True
        return False

    def event_log(self, notes):
        mysql.event_log({
            "event_type": f"{THIS_MODULE}/payment",
            "user_id": self.user_id,
            "who_did_it": "paypal/webhook",
            "notes": notes,
            "filename": self.filename
        })

    def read_payment_capture(self):
        resource = self.input["resource"]
        if "amount" not in resource or "value" not in resource["amount"] or "currency_code" not in resource["amount"]:
            return self.err_exit("Amount not found or invalid")
        amount = resource["amount"]
        currency = policy.policy("currency")
        if amount["currency_code"] != currency["iso"]:
            return self.err_exit("Currency mismatch {amount['currency_code']} is not {currency['iso']}")
        self.amount = misc.amt_from_float(amount["value"])

        self.desc = self.input["summary"] if "summary" in self.input else "Payment by PayPal"

        if "custom_id" not in resource:
            return self.err_exit("No custom_id found")

        self.token = resource["custom_id"]
        self.paypal_trans_id = self.input["id"] if "id" in self.input else self.token
        return True, True

    def set_token_seen(self):
        sql.sql_update_one("payments", {"token_type": static.PAY_TOKEN_SEEN_SINGLE}, {
            "user_id": self.user_id,
            "token": self.token,
            "provider": f"{THIS_MODULE}:single"
        })

    def payment_capture_completed(self):
        if not self.read_payment_capture():
            return False, self.msg
        if not self.get_user_id([static.PAY_TOKEN_SINGLE, static.PAY_TOKEN_SEEN_SINGLE], True):
            return False, f"Failed to match user to payment - {self.token}"
        self.event_log("Successfully matched user to payment")
        if not self.credit_users_account():
            return False, "Failed to credit users account"
        self.event_log("Successfully credited users account")
        return True, True

    def checkout_order_approved(self):
        if not self.read_checkout_order():
            return True, True

        if not self.get_user_id(static.PAY_TOKEN_SINGLE, False):
            return True, True

        self.store_users_identity()
        self.set_token_seen()
        if self.amount and self.currency:
            currency = policy.policy("currency")
            if self.currency == currency["iso"]:
                payfuncs.set_orders_status(self.user_id, self.amount, "authorised")
                messages.send(self.user_id, f"Payment of {misc.format_currency(self.amount,currency)} authorised")
        return True, True

    def process_webhook(self):
        log(f"PayPal Webhook: {self.input['event_type']}")
        if "resource" not in self.input:
            return False, "ERROR: PayPal record does not have 'resource'"

        if self.input["event_type"] == "CHECKOUT.ORDER.APPROVED":
            return self.checkout_order_approved()
        if self.input["event_type"] == "PAYMENT.CAPTURE.COMPLETED":
            return self.payment_capture_completed()

        return True, True


def process_webhook(headers, webhook_data, sent_data, filename):
    hook = PayPalWebHook(webhook_data, sent_data, filename)
    if not hook.interesting_webhook():
        return None, None
    return hook.process_webhook()


def single(user_id, description, amount):
    pay_db = {
        "provider": f"{THIS_MODULE}:single",
        "token": f"{misc.ashex(user_id)}.{hashstr.make_hash(length=30)}",
        "token_type": static.PAY_TOKEN_SINGLE,
        "user_id": user_id,
        "user_can_delete": False
    }

    ok, __ = sql.sql_insert("payments", pay_db)
    if not ok:
        return False, "Adding payments data failed"

    return True, pay_db


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "config": my_config,
    "startup": startup,
    "webhook": process_webhook,
    "single": single
})


def run_debug():
    log_init(with_debug=True)
    startup()
    sql.connect("engine")
    file = "/opt/github/pyrar/tmp/" + sys.argv[1]
    with open(file, "r", encoding="utf-8") as fd:
        print(process_webhook({}, json.load(fd), file))


if __name__ == "__main__":
    run_debug()
