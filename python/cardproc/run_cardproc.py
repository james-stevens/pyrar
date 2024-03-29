#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import argparse

from librar.mysql import sql_server as sql
from librar.log import log, init as log_init
from librar import sigprocs
from librar import accounts
from librar import sales
from librar import registry
from backend import backend_creator

DEFAULT_WAIT = 60


def get_next_order_to_clear():
    query = ("select orders.* from orders join users using(user_id) " +
             "where price_paid <= (acct_current_balance - acct_overdraw_limit) " + "order by order_item_id limit 1")
    return sql.run_select(query)


def process_order(order_db):
    ok, user_db = sql.sql_select_one("users", {"user_id": order_db["user_id"]})
    if not ok:
        return False, f"User {order_db['user_id']} not found"

    if order_db["price_paid"] > (user_db["acct_current_balance"] - user_db["acct_overdraw_limit"]):
        return False, (f"Insufficient balalnce: {order_db['price_paid']} > " +
                       f"{user_db['acct_current_balance']} - {user_db['acct_overdraw_limit']}")

    ok, dom_db = sql.sql_select_one("domains", {"domain_id": order_db["domain_id"]})
    if not ok:
        return False, f"Domain {order_db['domain_id']} not found"

    ok, trans_id = accounts.apply_transaction(
        user_db["user_id"], (-1 * order_db["price_paid"]),
        f"{order_db['order_type']} on {dom_db['name']} for {order_db['num_years']} yrs")

    if not ok:
        return False, f"Account debit failed - {trans_id}"

    ok, sold_id = sales.sold_item(trans_id, order_db, dom_db, user_db)
    if ok and sold_id:
        sql.sql_update_one("transactions", {"sales_item_id": sold_id}, {"transaction_id": trans_id})

    backend_creator.make_job(order_db["order_type"], dom_db, order_db["num_years"], order_db["authcode"])
    sql.sql_delete_one("orders", {"order_item_id": order_db["order_item_id"]})
    return True, "Worked"


def run_server(max_wait=DEFAULT_WAIT):
    log("PAY-ENGINE RUNNING")
    signal_mtime = None
    while True:
        ok, order_db = get_next_order_to_clear()
        if ok and len(order_db) > 0:
            ok, reply = process_order(order_db[0])
            if not ok:
                log(f"PAY-ENGINE ERR: {reply}")
        else:
            signal_mtime = sigprocs.signal_wait("payeng", signal_mtime, max_wait=max_wait)
            registry.tld_lib.check_for_new_files()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-D", '--debug', action="store_true")
    args = parser.parse_args()
    log_init(with_debug=args.debug)

    sql.connect("engine")
    registry.start_up()
    run_server(5 if args.debug else DEFAULT_WAIT)
