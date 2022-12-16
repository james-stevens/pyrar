#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json

from lib.log import log, debug, init as log_init
from lib import validate
from lib import misc
from lib import registry
from lib import mysql as sql
from lib.policy import this_policy as policy

import domains
import handler
# pylint: disable=unused-wildcard-import, wildcard-import
from plugins import *


def secure_orders_db_recs(orders):
    for order in orders:
        for block in ["price_charged","currency_charged"]:
            del order[block]



def make_blank_domain(name, user_id, can_process):
    dom_db = {
        "name": name,
        "user_id": user_id,
        "name_servers": policy.policy("dns_servers"),
        "auto_renew": 0,
        "status_id": misc.STATUS_WAITING_PROCESSING if can_process else misc.STATUS_WAITING_PAYMENT,
        "created_dt": None,
        "amended_dt": None,
        "expiry_dt": None
        }
    return sql.sql_insert("domains",dom_db)


def webui_basket(basket, user_id):
    ok, reply = capture_basket(basket, user_id)
    if not ok:
        return False, reply
    return save_basket(basket, user_id)


def save_basket(basket, user_id):
    for order in basket:
        order_db = order["order_db"]
        if order_db["domain_id"] == -1:
            ok, reply = make_blank_domain(order["domain"],user_id,order["processing"])
            if not ok:
                return False, f"Failed to reserve domain {order['domain']}"
            order_db["domain_id"] = reply
        ok, reply = sql.sql_insert("orders",order_db)
        if not ok:
            return False, reply

    return True, basket


def capture_basket(basket, user_id):
    if len(basket) > policy.policy("max_basket_size"):
        return False, "Basket too full"

    ok, sum_orders = sql.sql_select_one("orders", {"user_id": user_id}, "sum(price_paid) 'sum_orders'")
    if not ok:
        return False, sum_orders

    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok:
        return False, user_db

    availble_balance = user_db["acct_current_balance"] - user_db["acct_overdraw_limit"]

    if sum_orders["sum_orders"] is not None and sum_orders["sum_orders"] > availble_balance:
        return False, "Please pay for your existing orders before placing more orders"

    if user_db["acct_current_balance"] < user_db["acct_overdraw_limit"]:
        return False, "Please clear your debt before placing more orders"

    ok, reply = process_basket(basket, user_db)
    if not ok:
        return False, reply

    total = 0
    for order in reply:
        total += order["order_db"]["price_paid"]
        order["processing"] = (total < availble_balance)

    need_to_pay = 0
    fully_paid = (total <= availble_balance)
    if not fully_paid or user_db["acct_overdraw_limit"] > 0:
        need_to_pay = total - user_db["acct_current_balance"]

    return True, {"fully_paid": fully_paid, "need_to_pay": need_to_pay, "user": user_db, "basket": reply}


def check_basket_item(basket_item):
    for prop in ["domain", "num_years", "action", "cost"]:
        if prop not in basket_item:
            return False, "A:Basket seems to be corrupt"
    if (err := validate.check_domain_name(basket_item["domain"])) is not None:
        return False, err
    if not isinstance(basket_item["num_years"], int):
        return False, "B:Basket seems to be corrupt"
    if basket_item["action"] not in misc.EPP_ACTIONS:
        return False, "C:Basket seems to be corrupt"

    return True, None


def process_basket(basket, user_db):
    for order in basket:
        ok, reply = check_basket_item(order)
        if not ok:
            return False, reply

    for order in basket:
        ok, reply = price_order_item(order, user_db)
        if not ok:
            return False, reply
        order["prices"] = reply

    site_currency = policy.policy("currency")
    for order in basket:
        ok, reply = make_order_record(site_currency, order, user_db)
        if not ok:
            return False, reply
        order["order_db"] = reply

    for order in basket:
        if order["cost"] != order["order_db"]["price_paid"]:
            debug(f'{order["cost"]} is not {order["order_db"]["price_paid"]}')
            return False, "D:Basket seems to be corrupt"

    return True, basket


def price_order_item(order, user_db):
    domobj = domains.DomainName(order["domain"])
    if domobj.names is None:
        return False, domobj.err if domobj.err is not None else "Invalid domain name"

    if not domobj.registry or "type" not in domobj.registry or "name" not in domobj.registry:
        return False, "Registrar not supported"

    if (plugin_func := handler.run(domobj.registry["type"],"dom/price")) is None:
        return False, f"No plugin for this Registrar: {domobj.registry['name']}"

    ok, prices = plugin_func(domobj, order["num_years"], [order["action"]], user_db)
    if not ok or prices is None or len(prices) != 1:
        return False, "Price check failed"

    if order["action"] not in prices[0]:
        return False, f"Error in xml prices for: {order['domain']}/{order['action']}"

    registry.tld_lib.multiply_values(prices, order["num_years"], True)

    prices = prices[0]

    if "reg_" + order["action"] not in prices:
        return False, f"Error in json prices for: {order['domain']}/{order['action']}"

    prices["currency"] = domobj.currency["iso"]

    return True, prices


def get_order_domain_id(order, user_db):
    ok, dom_db = sql.sql_select_one("domains", {"name": order["domain"]})
    if not ok:
        return False, f"Domain database lookup error: {order['domain']}"

    match order["action"]:
        case "transfer":
            if dom_db["user_id"] == user_db["user_id"]:
                return False, "Domain is already yours: {order['domain']}/{order['action']}"

        case ["recover", "renew"]:
            if dom_db["user_id"] != user_db["user_id"]:
                return False, f"{dom_db['name']} is not your domain ({order['action']})"

        case "create":
            if len(dom_db) >= 1:
                return False, "Domain already exists: {order['domain']}/{order['action']}"
            return True, -1

    if "domain_id" in dom_db:
        return True, dom_db["domain_id"]

    return False, "No domain_id in domain record!?!?"


def make_order_record(site_currency, order, user_db):
    ok, order_domain_id = get_order_domain_id(order, user_db)
    if not ok:
        return False, order_domain_id

    if "prices" not in order:
        return False, "Missing prices"

    now = sql.now()
    prices = order["prices"]

    return True, {
        "price_charged": prices["reg_" + order["action"]],
        "price_paid": prices[order["action"]],
        "currency_charged": prices["currency"],
        "currency_paid": site_currency["iso"],
        "domain_id": order_domain_id,
        "user_id": user_db["user_id"],
        "order_type": f"dom/{order['action']}",
        "num_years": order["num_years"],
        "authcode": order["authcode"] if "autocode" in order else None,
        "created_dt": now,
        "amended_dt": now
    }


def run_test(which):
    if which != 1:
        ok, reply = webui_basket([{
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
        }], 10450)
    else:
        ok, reply = webui_basket([{"domain": "teams.zz", "num_years": 1, "cost": 1100, "action": "create"}], 10450)

    print(ok, json.dumps(reply, indent=3))
    sys.exit(0)


if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("webui")
    registry.start_up()
    # run_test(1)
    user_id = 10452
    ok, sum_orders = sql.sql_select_one("orders", {"user_id": user_id}, "sum(price_paid) 'sum_orders'")
    print(ok,sum_orders)
