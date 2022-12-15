#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json

from lib import validate
from lib import misc
from lib import registry
from lib import mysql as sql
from lib.policy import this_policy as policy

import domains

import handler
from plugins import *


def capture_basket(basket, user_id):
    ok, reply = sql.sql_select_one("order_items",{"user_id":user_id})
    if not ok:
        return False, reply

    if len(reply) >= 1:
        return False, "You already order items waitign to be paid for"

    ok, user_db = sql.sql_select_one("users",{"user_id":user_id})
    if not ok:
        return False, user_db

    if user_db["acct_current_balance"] < user_db["acct_overdraw_limit"]:
        return False, "Please clear your debt before placing more orders"

    ok, reply = process_basket(basket, user_db)
    if not ok:
        return False, reply

    total = 0
    for order in reply:
        total += order["order_db"]["price_paid"]
        if total < user_db["acct_current_balance"]:
            order["order_db"]["processing"] = True

    fully_paid = (total <= user_db["acct_current_balance"])
    if not fully_paid:
        need_to_pay = total - user_db["acct_current_balance"]

    return True, { "fully_paid":fully_paid, "need_to_pay":need_to_pay, "user": user_db, "basket": reply }



def check_basket_item(basket_item):
    for prop in ["domain", "num_years", "action"]:
        if prop not in basket_item:
            return False, "Basket seems to be corrupt"
    if (err := validate.check_domain_name(basket_item["domain"])) is not None:
        return False, err
    if not isinstance(basket_item["num_years"], int):
        return False, "Basket seems to be corrupt"
    if basket_item["action"] not in misc.EPP_ACTIONS:
        return False, "Basket seems to be corrupt"
    return True, None


def process_basket(basket,user_db):
    for order in basket:
        ok, reply = check_basket_item(order)
        if not ok:
            return False, reply

    for order in basket:
        ok, reply = price_order_item(order,user_db)
        if not ok:
            return False, reply
        else:
            order["prices"] = reply

    site_currency = policy.policy("currency",misc.DEFAULT_CURRENCY)
    for order in basket:
        ok, reply = make_order_record(site_currency, order, user_db)
        if not ok:
            return False, reply
        else:
            order["order_db"] = reply

    return True, basket


def price_order_item(order,user_db):
    domobj = domains.DomainName(order["domain"])

    if not domobj.registry or "type" not in domobj.registry or "name" not in domobj.registry:
        return False, "Registrar not supported"

    reg_type = domobj.registry["type"]
    if reg_type not in handler.plugins or "dom/price" not in handler.plugins[reg_type]:
        return False, "No plugin for this Registrar: {domobj.registry['name']}"

    handler.plugins[domobj.registry["type"]]["dom/price"]
    ok, prices = handler.plugins[reg_type]["dom/price"](domobj, order["num_years"], [order["action"]], user_db)
    if not ok or prices is None or len(prices) != 1:
        return False, "Price check failed"

    if order["action"] not in prices[0]:
        return False, f"Error in xml prices for: {order['domain']}/{order['action']}"

    registry.tld_lib.multiply_values(prices, order["num_years"], True)

    prices = prices[0]

    if "reg_"+order["action"] not in prices:
        return False, f"Error in json prices for: {order['domain']}/{order['action']}"

    prices["currency"] = domobj.currency["iso"]

    return True, prices


def create_inactive_domain(order):
    return 99999


def get_order_domain_id(order,user_db):
    ok, dom_db = sql.sql_select_one("domains",{"name":order["domain"]})
    if not ok:
        return False, f"Domain database lookup error: {order['domain']}"

    if order["action"] == "transfer" and dom_db["user_id"] == user_db["user_id"]:
        return False, "Domain is already yours: {order['domain']}/{order['action']}"

    if order["action"] in ["recover","renew"] and dom_db["user_id"] != user_db["user_id"]:
        return False, f"{dom_db['name']} is not your domain ({order['action']})"

    if order["action"] == "create":
        if len(dom_db) >= 1:
            return False, "Domain already exists: {order['domain']}/{order['action']}"
        else:
            return True, -1

    if "domain_id" in dom_db:
        return True, dom_db["domain_id"]

    return False, "No domain_id in domain record!?!?"


def make_order_record(site_currency, order,user_db):
    ok, order_domain_id = get_order_domain_id(order,user_db)
    if not ok:
        return False, order_domain_id

    if "prices" not in order:
        return False, "Missing prices"

    now = sql.now()
    prices = order["prices"]

    return True, {
        "price_charged": prices["reg_"+order["action"]],
        "price_paid": prices[order["action"]],
        "currency_charged": prices["currency"],
        "currency_paid": site_currency["iso"],
        "domain_id": order_domain_id,
        "user_id": user_db["user_id"],
        "order_type": f"dom/{order['action']}",
        "num_years": order["num_years"],
        "authcode": order["authcode"] if "autocode" in order else None,
        "processing": False,
        "created_dt": now, "amended_dt": now
        }



if __name__ == "__main__":
    sql.connect("webui")
    registry.start_up()

    ok, reply = capture_basket([{
        "domain": "xn--dp8h.xn--dp8h",
        "num_years": 1,
        "cost": "1100",
        "action": "renew"
    }, {
        "domain": "teams.zy",
        "num_years": 1,
        "cost": "1200",
        "action": "create"
    }, {
        "domain": "teams.xp",
        "num_years": 1,
        "cost": "11000",
        "action": "create"
    }, {
        "domain": "teams.chug",
        "num_years": 1,
        "cost": "2000",
        "action": "create"
    }],10450)

    print(json.dumps(reply,indent=3))

    sys.exit(0)

    ok, reply = capture_basket([{
        "domain": "teams.xp",
        "num_years": 1,
        "cost": 1100,
        "action": "create"
        }],10450)


