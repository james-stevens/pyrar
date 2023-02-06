#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar.policy import this_policy as policy
from librar import mysql as sql
from librar import validate
from librar import static_data
from librar import accounts


def find_payment_record(injs):
    if "provider_tag" not in injs or not validate.is_valid_display_name(injs["provider_tag"]):
        return False, "Insufficient or invalid data"

    where = { "provider_tag": injs[provider_tag] }
    if "provider" in injs:
        where["provider"] = injs["provider"]

    ok, pay_db = sql.sql_select_one("payments",where)
    if ok and pay_db and len(pay_db) > 0:
        return True, pay_db

    return False, "No matching user found"


def process(injs):
    if injs is None or not sql.has_data(injs, ["amount", "description"]):
        return False, "Missing or invalid data"

    if (amount := validate.valid_float(injs["amount"])) is None:
        return False, "Invalid amount"
    if not validate.is_valid_display_name(injs["description"]):
        return False, "Invalid description"

    pay_db = None
    if "user_id" in injs:
        user_id = injs["user_id"]
        if not isinstance(user_id, int):
            return False, "Missing or invalid data"
    else:
        ok, pay_db = find_payment_record(injs)
        if not ok:
            return False, pay_db
        user_id = pay_db["user_id"]

    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok or not user_db or len(user_db) <= 0:
        return False, "Invalid user_id given"

    site_currency = policy.policy("currency")
    amount *= static_data.POW10[site_currency["decimal"]]
    amount = int(round(amount, 0))

    ok, trans_id = accounts.apply_transaction(user_id, amount, "Admin: " + injs["description"], as_admin=True)
    if not ok:
        return False, trans_id

    if pay_db is not None:
        if pay_db["single_use"]:
            sql.sql_update_one("payments", {
                "provider": "DONE:"+pay_db["provider"],
                "provider_tag": "DONE:"+pay_db["provider_tag"],
                "amended_dt": None
                }, { "payment_id": pay_db["payment_id"] })

    return True, True
