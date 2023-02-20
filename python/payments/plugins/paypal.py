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


def paypal_process_webhook():
    # CODE
    return True


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "config": paypal_config,
    "startup": paypal_startup,
    "process": paypal_process_webhook,
})
