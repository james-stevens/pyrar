#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar.policy import this_policy as policy

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


def check_web_hook_data(sent_data):
    if len(sent_data["purchase_units"] != 1:
        log("ERROR: PayPal record does have one 'purchase_units'")
        return False

    pay_unit = sent_data["purchase_units"][0]
    if "amount" not in pay_unit or not isinstance(pay_unit["amount"],dict):
        log("ERROR: PayPal 'amount' record missing or invalid")
        return False

    currency = policy.policy("currency")
    if "currency" not in pay_unit["amount"] or pay_unit["amount"]["currency"] != currency["iso"]:
        log(f"ERROR: PayPal currency missing or doesn't match '{currency['iso']}'")
        return False

    if "value" not in pay_unit["amount"]:
        log(f"ERROR: PayPal amount has no 'value' field")
        return False

    if "custom_id" not in pay_unit:
        log(f"ERROR: PayPal purchase_unit has no 'custom_id' field")



def paypal_process_webhook(sent_data):
    if not check_web_hook_data(sent_data):
        return False
    return True


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "config": paypal_config,
    "startup": paypal_startup,
    "webhook": paypal_process_webhook,
})
