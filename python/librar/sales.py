#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar import sigprocs
from librar import registry
from librar import mysql as sql


def make_epp_job(order_db):
    epp_job = {
        "domain_id": order_db["domain_id"],
        "user_id": order_db["user_id"],
        "job_type": order_db["order_type"],
        "num_years": order_db['num_years'],
        "authcode": order_db["authcode"],
        "failures": 0,
        "execute_dt": sql.now(),
        "created_dt": None,
        "amended_dt": None
    }

    sql.sql_insert("epp_jobs", epp_job)
    sigprocs.signal_service("backend")


def sold_item(trans_id, order_db, domain_name, user_email):
    sales = {
        "transaction_id": trans_id,
        "price_charged": order_db["price_charged"],
        "currency_charged": order_db["currency_charged"],
        "price_paid": order_db["price_paid"],
        "currency_paid": order_db["currency_paid"],
        "domain_name": domain_name,
        "zone_name": registry.tld_lib.tld_of_name(domain_name),
        "user_email": user_email,
        "sales_type": order_db['order_type'],
        "num_years": order_db['num_years'],
        "created_dt": None,
        "amended_dt": None
    }

    return sql.sql_insert("sales", sales)
