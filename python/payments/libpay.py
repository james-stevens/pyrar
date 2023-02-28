#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

import os
import json
import tempfile

from librar import misc
from librar.log import log, debug, init as log_init
from librar.mysql import sql_server as sql
from mailer import spool_email
from payments import payfile

from payments import pay_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from payments.plugins import *

HAS_RUN_START_UP = False

def set_orders_status(user_id,amount_paid,new_status):
    ok, user_db = sql.sql_select_one("users",{"user_id":user_id})
    if not ok:
        return False

    ok, orders_db = sql.sql_select("orders",{ "user_id":user_id,"status":None },order_by="order_item_id")
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
    sql.sql_update("orders",{"status":new_status},{"user_id":user_id,"status":None,"order_item_id":change_status})


def startup():
    global HAS_RUN_START_UP
    for module in [mod for mod in payfile.payment_file.data() if mod in pay_handler.pay_plugins]:
        if (func := pay_handler.run(module, "startup")) is not None:
            func()
    HAS_RUN_START_UP = True


def config():
    if not HAS_RUN_START_UP:
        startup()

    all_config = {}
    for module in [mod for mod in payfile.payment_file.data() if mod in pay_handler.pay_plugins]:
        all_config[module] = None
        if (func := pay_handler.run(module, "config")) is not None:
            all_config[module] = func()
    return all_config


def process_webhook(webhook_data, sent_data):
    if "name" not in webhook_data:
        return False, "Webhook data has no 'name' property"

    pay_module = webhook_data["name"]
    file_name = None
    with tempfile.NamedTemporaryFile("w+",
                                     encoding="utf-8",
                                     dir=misc.make_year_month_day_dir(
                                         os.path.join(os.environ["BASE"], "storage/perm/payments")),
                                     delete=False,
                                     prefix=pay_module + "_") as fd:
        file_name = fd.name
        os.chmod(file_name, 0o755)
        if isinstance(sent_data, str):
            fd.write(sent_data)
        else:
            json.dump(sent_data, fd)

    if (func := pay_handler.run(pay_module, "webhook")) is None:
        return False, f"Webhook for'{pay_module}' module is not set up"

    ok, reply = func(webhook_data, sent_data, file_name)
    if ok is None and reply is None:
        os.remove(file_name)
        return True, True

    if ok:
        return True, "Processed"

    if file_name is not None:
        spool_email.spool("admin_webhook_failed",
                          [[None, {
                              "filename": file_name,
                              "pay_module": pay_module,
                              "message": reply
                          }]])

    log(f"WebHook Processing Error - {reply}")
    return False, f"Call to Webhook for '{pay_module}' failed"


def main():
    log_init(with_debug=True)
    sql.connect("engine")
    startup()
    set_orders_status(10452,10000,"authorised")


if __name__ == "__main__":
    main()
