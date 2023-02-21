#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import argparse

from librar import mysql as sql
from librar.log import init as log_init
from librar.policy import this_policy as policy


def remove_old_one_time_payment_keys():
    query = "delete from payments where single_use and created_dt < date_sub(now(), interval 7 day)"
    return sql.sql_exec(query)


def clear_old_session_keys():
    tout = policy.policy('session_timeout') * 2
    query = f"delete from session_keys where amended_dt < date_sub(now(), interval {tout} minute)"
    return sql.sql_exec(query)


def cancel_unpaid_orders():
    tout = policy.policy('create_expire_days')
    query = f"delete from orders where order_type = 'dom/create' and created_dt < date_sub(now(), interval {tout} day)"
    sql.sql_exec(query)
    tout = policy.policy('orders_expire_days')
    query = f"delete from orders where order_type <> 'dom/create' and created_dt < date_sub(now(), interval {tout} day)"
    return sql.sql_exec(query)


def run_all_jobs():
    clear_old_session_keys()
    cancel_unpaid_orders()
    remove_old_one_time_payment_keys()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-D", '--debug', action="store_true")
    args = parser.parse_args()
    log_init(with_debug=args.debug)
    sql.connect("engine")
    run_all_jobs()
