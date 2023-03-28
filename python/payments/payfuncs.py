#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

from librar import static, fileloader
from librar.mysql import sql_server as sql


def set_orders_status(user_id, amount_paid, new_status):
    """ mark payments {new_status} up to {amount_paid} """
    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok:
        return False

    ok, orders_db = sql.sql_select("orders", {"user_id": user_id}, order_by="order_item_id")
    if not ok or len(orders_db) <= 0:
        return False

    change_status = []
    cur_bal = user_db["acct_current_balance"] + amount_paid
    for order_db in orders_db:
        next_bal = cur_bal - order_db["price_paid"]
        if next_bal < user_db["acct_overdraw_limit"]:
            break
        cur_bal = next_bal
        change_status.append(order_db["order_item_id"])

    sql.sql_update("orders", {"status": new_status}, {"user_id": user_id, "order_item_id": change_status})
    return True


payment_file = fileloader.FileLoader(static.PAYMENT_FILE)
