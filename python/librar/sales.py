#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions for recording & handling sales """

from mailer import spool_email
from librar import registry
from librar import mysql
from librar.mysql import sql_server as sql


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
        "user_id": user_db["user_id"],
        "user_email": user_db["email"],
        "sales_type": order_db['order_type'],
        "num_years": order_db['num_years'],
        "been_refunded": False
    }

    ok, row_id = sql.sql_insert("sales", sales)

    mysql.event_log(
        {
            "event_type": order_db['order_type'],
            "notes": f"Sale: {dom_db['name']} sold with {order_db['order_type']} for {order_db['num_years']} yrs",
            "domain_id": dom_db["domain_id"],
            "user_id": dom_db["user_id"],
            "who_did_it": "sales",
            "from_where": "localhost"
        }, 1)

    spool_email.spool("receipt", [["sales", {
        "sales_item_id": row_id
    }], ["domains", {
        "domain_id": dom_db["domain_id"]
    }], ["users", {
        "user_id": dom_db["user_id"]
    }]])

    return ok, row_id
