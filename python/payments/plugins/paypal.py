#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar import validate
from librar import mysql as sql
from librar.policy import this_policy as policy
from librar import hashstr
from librar import misc

from payments import pay_handler

THIS_MODULE = "paypal"


def paypal_topup(user_id):
    return paypal_topup(user_id,amount_owed)


def paypal_topup(user_id,amount):
    business_name = policy.policy("business_name")
    random_str = hashstr.make_hash(chars_needed=30)
    currency = policy.policy("currency")
    fmt_amt = misc.format_currency(amount,currency,with_symbol=False)

    return True, {
        "html": '<div id="paypal-button-container"></div>',
        "script": f"initPayPalButton('Top-Up: {business_name}','{random_str}',{fmt_amt},'{currency['iso']}')"
    }


pay_handler.add_plugin(THIS_MODULE, {
    "desc": "PayPal",
    "paynow": paypal_paynow_html,
    "autopay": paypal_auto_html,
})
