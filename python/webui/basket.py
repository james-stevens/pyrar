#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json

from librar.log import log, init as log_init
from librar import validate, misc, static, registry, accounts, sales, domobj, mysql
from librar.mysql import sql_server as sql
from librar.policy import this_policy as policy
from backend import backend_creator, libback
from actions import make_actions

MANDATORY_BASKET = ["domain", "num_years", "action", "cost"]


def make_blank_domain(name, user_db, status_id, num_years):
    dom_db = {
        "name": name,
        "user_id": user_db["user_id"],
        "ns": policy.policy("dns_servers"),
        "auto_renew": user_db["default_auto_renew"],
        "status_id": status_id,
        "expiry_dt": None
    }
    ok, dom_id = sql.sql_insert("domains", dom_db)
    if ok:
        dom_db["domain_id"] = dom_id

    dom_db["created_dt"] = misc.now()
    dom_db["expiry_dt"] = misc.date_add(dom_db["created_dt"], years=num_years)
    return ok, dom_db


def event_log(req, order):
    event_db = req.base_event.copy()
    event_db.update({
        "domain_id": order["dom_db"]["domain_id"] if "dom_db" in order else None,
        "event_type": f"order/{order['action']}",
        "notes": f"Order: {order['domain']} of {order['action']} for {order['num_years']} yrs"
    })
    mysql.event_log(event_db)


def webui_basket(basket, req):
    ok, user_db = sql.sql_select_one("users", {"user_id": req.user_id})
    if not ok:
        return False, user_db

    if user_db["acct_on_hold"]:
        return False, "Account is on hold"

    whole_basket = {"basket": basket, "user_db": user_db}

    ok, reply = capture_basket(req, whole_basket)
    if not ok:
        return False, reply

    basket[:] = [order for order in basket if "paid-for" not in order]

    if len(basket) > 0:
        ok, reply = save_basket(req, whole_basket)
        if not ok:
            return False, reply

    return True, basket


def save_basket(req, whole_basket):
    basket = whole_basket["basket"]
    user_db = whole_basket["user_db"]
    for order in basket:
        if "failed" in order or "paid-for" in order:
            continue

        order_db = order["order_db"]
        if "domain_id" in order_db and order_db["domain_id"] is None:
            ok, dom_db = make_blank_domain(order["domain"], user_db, static.STATUS_WAITING_PAYMENT,
                                           order_db["num_years"])
            if not ok:
                return False, f"Failed to reserve domain {order['domain']}"
            order_db["domain_id"] = dom_db["domain_id"]
            order["dom_db"] = dom_db
        ok, order_item_id = sql.sql_insert("orders", order_db)
        if not ok:
            return False, order_item_id
        order_db["order_item_id"] = order_item_id
        event_log(req, order)
        make_actions.recreate(order["dom_db"])

    return True, True


def capture_basket(req, whole_basket):
    basket = whole_basket["basket"]
    user_db = whole_basket["user_db"]

    if len(basket) > policy.policy("max_basket_size"):
        return False, "Basket too full - please remove one or more items"

    ok, sum_db = sql.sql_select_one("orders", {"user_id": user_db["user_id"]}, "sum(price_paid) 'sum_orders'")
    if not ok or sum_db is None:
        return False, "Failed to read database"

    sum_orders = sum_db["sum_orders"] if misc.has_data(sum_db, "sum_orders") else 0

    if sum_orders > (user_db["acct_current_balance"] - user_db["acct_overdraw_limit"]):
        return False, "Please pay for your existing orders before placing more orders"

    if user_db["acct_current_balance"] < user_db["acct_overdraw_limit"]:
        return False, "Please clear your account debt before placing more orders"

    if not (reply := parse_basket(whole_basket))[0]:
        return False, reply[1]

    live_process_basket(req, whole_basket)
    return True, basket


def live_process_basket(req, whole_basket):
    user_db = whole_basket["user_db"]
    basket = whole_basket["basket"]
    for order in basket:
        if "failed" not in order and pay_for_basket_item(req, order, user_db) is None:
            order["failed"] = "Paying for item failed"


def pay_for_basket_item(req, order, user_db):
    if "failed" in order:
        return False

    order_db = order["order_db"]
    if (user_db["acct_current_balance"] - user_db["acct_overdraw_limit"]) < order_db["price_paid"]:
        return False

    ok, trans_id = accounts.apply_transaction(
        user_db["user_id"], (-1 * order_db["price_paid"]),
        f"{order_db['order_type']} on {order['domain']} for {order_db['num_years']} yrs")

    if not ok or not trans_id:
        return False

    user_db["acct_previous_balance"] = user_db["acct_current_balance"]
    user_db["acct_current_balance"] -= order_db["price_paid"]

    if order_db['order_type'] == "dom/transfer":
        ok, dom_db = make_blank_domain(order['domain'], user_db, static.STATUS_TRANS_QUEUED, order_db["num_years"])
        if not ok:
            return False
        order_db["domain_id"] = dom_db["domain_id"]
        order["dom_db"] = dom_db
    elif order_db['order_type'] == "dom/create":
        ok, dom_db = make_blank_domain(order['domain'], user_db, static.STATUS_LIVE, order_db["num_years"])
        if not ok:
            return False
        order_db["domain_id"] = dom_db["domain_id"]
        order["dom_db"] = dom_db

    ok, sold_id = sales.sold_item(trans_id, order_db, order["dom_db"], user_db)
    if ok and sold_id:
        sql.sql_update("transactions", {"sales_item_id": sold_id}, {"transaction_id": trans_id})

    event_log(req, order)
    order["paid-for"] = True
    backend_creator.make_job(order_db["order_type"], order_db, order_db["num_years"], order_db["authcode"])
    return True


def check_basket_item(basket_item):
    if len(basket_item) != len(MANDATORY_BASKET):
        return False, "Basket seems to be corrupt"
    for prop in MANDATORY_BASKET:
        if prop not in basket_item:
            return False, "Basket seems to be corrupt"
    if (err := validate.check_domain_name(basket_item["domain"])) is not None:
        return False, err
    if not isinstance(basket_item["num_years"], int):
        return False, "Basket seems to be corrupt"
    if basket_item["action"] not in static.DOMAIN_ACTIONS:
        return False, "Basket seems to be corrupt"

    return True, None


def parse_basket(whole_basket):
    basket = whole_basket["basket"]
    user_db = whole_basket["user_db"]
    for order in basket:
        ok, reply = check_basket_item(order)
        if not ok:
            order["failed"] = reply

    for order in basket:
        if "failed" in order:
            continue
        ok, reply = price_order_item(order)
        if not ok:
            log(reply)
            order["failed"] = "Price failed"
        else:
            order["prices"] = reply

    site_currency = policy.policy("currency")
    for order in basket:
        if "failed" in order:
            continue
        ok, reply = make_order_record(site_currency, order, user_db)
        if not ok:
            order["failed"] = reply
        else:
            order["order_db"] = reply

    for order in basket:
        if "failed" not in order and order["cost"] != order["order_db"]["price_paid"]:
            order["failed"] = "Cost mismatch"

    return True, basket


def price_order_item(order):
    doms = domobj.DomainList()
    ok, reply = doms.set_list(order["domain"])
    if not ok:
        return False, reply if reply is not None else "Invalid domain name"

    if not doms.registry or "type" not in doms.registry or "name" not in doms.registry:
        return False, "Registrar not supported"

    if not doms.domobjs[order["domain"]].valid_expiry_limit(order["num_years"]):
        return False, "Expiry limit exceeded"

    ok, prices = libback.get_prices(doms, order["num_years"], [order["action"]])
    if not ok or prices is None or len(prices) != 1:
        return False, "Price check failed"

    if order["action"] not in prices[0]:
        return False, f"Error in price sent for: {order['domain']}/{order['action']}"

    registry.tld_lib.multiply_values(prices, order["num_years"], True)

    prices = prices[0]

    if "reg_" + order["action"] not in prices:
        return False, f"Error in json prices for: {order['domain']}/{order['action']}"

    prices["currency"] = doms.currency["iso"]

    return True, prices


def get_order_domain_id(order, user_db):
    ok, dom_db = sql.sql_select_one("domains", {"name": order["domain"]})
    if not ok or not dom_db:
        return False, None

    order["dom_db"] = dom_db

    if order["action"] == "transfer":
        if dom_db["user_id"] == user_db["user_id"]:
            return False, f"Domain is already yours: {order['domain']}/{order['action']}"
    elif order["action"] in ["recover", "renew"]:
        if dom_db["user_id"] != user_db["user_id"]:
            return False, f"{dom_db['name']} is not your domain ({order['action']})"
    elif order["action"] == "create":
        if len(dom_db) >= 1:
            return False, f"Domain already exists: {order['domain']}/{order['action']}"
        return True, -1

    if "domain_id" in dom_db:
        return True, dom_db["domain_id"]

    return False, "No domain_id in domain record!?!?"


def make_order_record(site_currency, order, user_db):
    ok, order_domain_id = get_order_domain_id(order, user_db)
    if not ok and order_domain_id:
        return False, order_domain_id

    if "prices" not in order:
        return False, "Failed to verify price"

    now = misc.now()
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
        "status": "unpaid",
        "created_dt": now,
        "amended_dt": now
    }


class Empty:
    pass


def run_test(which):
    req = Empty
    req.user_id = 10450
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
        }], req)
    else:
        ok, reply = webui_basket([{"domain": "ty.zz", "num_years": 1, "cost": 1100, "action": "create"}], req)

    print(ok, json.dumps(reply, indent=3))
    sys.exit(0)


def main():
    log_init(with_debug=True)
    sql.connect("webui")
    registry.start_up()
    run_test(1)
    # user_id = 10452
    # ok, sum_orders = sql.sql_select_one("orders", {"user_id": user_id}, "sum(price_paid) 'sum_orders'")
    # print(ok,sum_orders)


if __name__ == "__main__":
    main()
