#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions for recording & handling sales """

import inspect

from mailer import spool_email
from librar import sigprocs
from librar import registry
from librar import mysql as sql


def make_backend_job(order_db):
    bke_job = {
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

    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")


def sold_item(trans_id, order_db, dom_db, user_db):
    this_reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    sales = {
        "transaction_id": trans_id,
        "price_charged": order_db["price_charged"],
        "currency_charged": order_db["currency_charged"],
        "price_paid": order_db["price_paid"],
        "currency_paid": order_db["currency_paid"],
        "domain_name": dom_db["name"],
        "domain_id": dom_db["domain_id"],
        "zone_name": registry.tld_lib.tld_of_name(dom_db["name"]),
        "registry": this_reg["name"] if this_reg is not None and "name" in this_reg else "Unknown",
        "user_email": user_db["email"],
        "sales_type": order_db['order_type'],
        "num_years": order_db['num_years'],
        "created_dt": None,
        "amended_dt": None
    }

    where = inspect.stack()[1]
    event_db = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None,
        "event_type": order_db['order_type'],
        "notes": f"Sale: {dom_db['name']} sold with {order_db['order_type']} for {order_db['num_years']} yrs",
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "who_did_it": "sales",
        "from_where": "localhost"
    }
    sql.sql_insert("events", event_db)

    ok, row_id = sql.sql_insert("sales", sales)

    spool_email.spool("receipt", [["sales", {
        "sales_item_id": row_id
    }], ["domains", {
        "domain_id": dom_db["domain_id"]
    }], ["users", {
        "user_id": dom_db["user_id"]
    }]])

    return ok, row_id
