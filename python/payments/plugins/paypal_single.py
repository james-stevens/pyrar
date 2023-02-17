#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import jinja2

from librar import validate
from librar import mysql as sql
from librar import policy
from librar import hashstr

from payments import pay_handler


THIS_MODULE = "paypal"

def paypal_single_html(user_id):
    merge_data = { "unique_id": hashstr.make_hash(chars_needed=30) }
    merge_data["policy"] = policy.policy_defaults
    merge_data["policy"].update(policy.this_policy.data())

    pay_conf = pay_handler.payment_file.data()
    if not isinstance(pay_conf,dict) or THIS_MODULE not in pay_conf:
        return False, "Payment module config is incomplete"

    my_conf = pay_conf[THIS_MODULE]
    mode = my_conf["mode"] if "mode" in my_conf else "live"
    if mode not in my_conf:
        return False, "Payment module config is incomplete"

    merge_data["payment"] = my_conf[mode]
    merge_data["currency"] = policy.this_policy.policy("currency")

    return True, {
    	"html": '<div id="smart-button-container"><div style="text-align: center;"><div id="paypal-button-container"></div></div></div>',
    	"script": 'initPayPalButton()'
    	}


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "single": paypal_single_html,
})
