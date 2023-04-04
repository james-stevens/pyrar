#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import requests

from librar.policy import this_policy as policy
from librar.log import log, init as log_init
from librar import misc, static, accounts, hashstr
from librar.mysql import sql_server as sql
from mailer import spool_email

from payments import pay_handler

THIS_MODULE = "nowpayment"

RETURN_PROPERTIES = ["id", "invoice_url", "order_id"]


def get_config():
    if (my_conf := pay_handler.module_config(THIS_MODULE)) is None:
        return None
    return_conf = {"desc": "Pay by Crypto via NowPayments"}
    if my_conf["mode"] == "test":
        return_conf["desc"] = "Pay by Crypto via NowPayments SandBox"
    return return_conf if "api_key" in my_conf else None


def startup():
    return True


def single(user_id, description, amount):
    if (my_conf := pay_handler.module_config(THIS_MODULE)) is None:
        return None

    if not misc.has_data(my_conf, ["api_key", "webhook"]):
        return None

    url = "https://api-sandbox.nowpayments.io/v1/invoice"
    headers = {"x-api-key": my_conf["api_key"], "Content-Type": "application/json"}

    token = f"{misc.ashex(user_id)}.{hashstr.make_hash(length=30)}"
    call_back = policy.policy("website_name") + f"pyrar/v1.0/hookid/{my_conf['webhook']}/{token}/"
    order_id = hashstr.make_hash(length=20)

    currency = policy.policy("currency")
    post_data = {
        "price_amount": misc.format_currency(amount, currency, with_symbol=False),
        "price_currency": currency["iso"],
        "ipn_callback_url": call_back,
        "success_url": policy.policy("website_name") + "nowpayment.html",
        "order_id": order_id,
        "order_description": description
    }

    try:
        resp = requests.request("POST", url, headers=headers, data=json.dumps(post_data))
        if resp.status_code < 200 or resp.status_code > 299:
            return False, "Creating transaction at NowPayments failed"

        resp_js = json.loads(resp.content.decode("utf-8"))
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return False, "Bad response from NowPayments"

    if not misc.has_data(resp_js, RETURN_PROPERTIES):
        return False, "Bad response from NowPayments"

    pay_db = {
        "provider": f"{THIS_MODULE}:single",
        "token": token,
        "token_type": static.PAY_TOKEN_SINGLE,
        "user_id": user_id,
        "user_can_delete": False
    }
    ok, __ = sql.sql_insert("payments", pay_db)
    if not ok:
        return False, "Failed to save payment details"

    return True, {prop: resp_js[prop] for prop in RETURN_PROPERTIES}


class NowPaymentWebHook:
    def __init__(self, headers, webhook_data, sent_json, filename):
        self.headers = headers
        self.input = sent_json
        self.webhook_data = webhook_data
        self.filename = filename

    def check(self):
        if not misc.has_data(self.headers, ["x-nowpayments-sig", "hook_trans_id"]):
            return False, "Header items missing"
        if not misc.has_data(self.input, [
                "payment_status", "invoice_id", "payment_id", "pay_address", "pay_currency", "order_id",
                "price_amount", "price_currency"
        ]):
            return False, "Record items missing"

        if self.input["payment_status"] != "finished":
            return False, "Payment status is not 'finished'"

        return True, True

    def process(self):
        ok, reply = self.check()
        if not ok:
            return False, reply

        log(f"SHA512: {self.headers['x-nowpayments-sig']}")

        currency = policy.policy("currency")
        price_currency = self.input["price_currency"].upper()
        if price_currency != currency["iso"]:
            return False, "Payment currency does not match"

        token = self.headers["hook_trans_id"]

        ok, pay_db = sql.sql_select_one(
            "payments", {
                "provider": f"{THIS_MODULE}:single",
                "token": token,
                "token_type": [static.PAY_TOKEN_SINGLE, static.PAY_TOKEN_SEEN_SINGLE],
                "user_can_delete": False
            })

        if not ok or len(pay_db) <= 0:
            return False, "Failed to find matching payment"

        amount = misc.amt_from_float(self.input["price_amount"])
        user_id = pay_db["user_id"]

        desc = (f"NowPayments: Paid {self.input['pay_amount']} in {self.input['pay_currency'].upper()} " +
                f"for {amount} in {price_currency}")

        ok, trans_id = accounts.apply_transaction(user_id, amount, desc, as_admin=True)
        if not ok:
            return False, "Crediting user account failed"

        sql.sql_delete_one("payments", {"payment_id": pay_db["payment_id"]})

        wallet_db = {
            "user_id": user_id,
            "provider": f"{THIS_MODULE}:{self.input['pay_currency']}",
            "token": self.input['pay_address'],
            "token_type": static.PAY_TOKEN_VERIFIED,
            "user_can_delete": True
        }
        sql.sql_insert("payments", wallet_db, ignore=True)

        spool_email.spool("payment_done", [["users", {
            "user_id": user_id
        }], ["transactions", {
            "transaction_id": trans_id
        }], [None, {
            "provider": THIS_MODULE,
            "provider_trans_id": self.input['payment_id']
        }]])

        return True, True


def process_webhook(headers, webhook_data, sent_data, filename):
    hook = NowPaymentWebHook(headers, webhook_data, sent_data, filename)
    return hook.process()


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "NowPayments",
    "config": get_config,
    "startup": startup,
    "webhook": process_webhook,
    "single": single
})


def run_debug():
    log_init(with_debug=True)
    sql.connect("engine")
    startup()
    if len(sys.argv) <= 1:
        ok, reply = single(10450, "Some Desc", 1891)
        print(ok)
        if ok:
            print(json.dumps(reply, indent=3))
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as fd:
            injs = json.load(fd)
            print(process_webhook(injs["header"], {}, injs["data"], sys.argv[1]))


if __name__ == "__main__":
    run_debug()
