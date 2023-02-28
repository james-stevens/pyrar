#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar.log import init as log_init
from librar.policy import this_policy as policy
from librar.mysql import sql_server as sql
from librar import misc
from librar import sigprocs
from librar import static
from librar import validate


def apply_transaction(user_id, amount, desc, as_admin=False):
    set_clauses = [
        "acct_previous_balance = (@prev := acct_current_balance)",
        f"acct_current_balance = (@newbal := acct_current_balance + {amount})",
        "acct_sequence_id = (@trnum := acct_sequence_id + 1)", "amended_dt = now()"
    ]

    where_clauses = [
        f"user_id = {user_id}", "not account_closed", "not acct_on_hold",
        f"(acct_current_balance + {amount}) >= acct_overdraw_limit"
    ]
    admin_where = [f"user_id = {user_id}"]

    where = " and ".join(admin_where) if as_admin else " and ".join(where_clauses)
    set_vals = ",".join(set_clauses)
    sql_cmd = f"update users set {set_vals} where {where} limit 1"
    row_count, row_id = sql.sql_exec(sql_cmd)

    if row_count is None:
        return False, "SQL failure debiting account"
    if not row_count:
        return False, "Account debit failed"

    set_trans = [
        f"user_id = {user_id}", "acct_sequence_id = @trnum", f"amount = {amount}", "pre_balance = @prev",
        "post_balance = @newbal", "description = unhex('" + misc.ashex(desc.encode("utf8")) + "')",
        "created_dt = now()"
    ]
    sql_cmd = "insert into transactions set " + ",".join(set_trans)

    row_count, row_id = sql.sql_exec(sql_cmd)
    if not row_count or not row_id:
        return False, row_id

    sql.sql_exec("select @trnum=NULL,@newbal=NULL,@prev=NULL")

    if amount > 0:
        sigprocs.signal_service("payeng")

    return True, row_id


def find_payment_record(injs):
    if "token" not in injs or not validate.is_valid_display_name(injs["token"]):
        return False, "Insufficient or invalid data"

    where = {"token": injs["token"]}
    if "provider" in injs:
        where["provider"] = injs["provider"]

    ok, pay_db = sql.sql_select_one("payments", where)
    if ok and pay_db and len(pay_db) > 0:
        return True, pay_db

    return False, "No matching user found"


def admin_trans(injs):
    if injs is None or not misc.has_data(injs, ["amount", "description"]):
        return False, "Missing or invalid data"

    if (amount := validate.valid_float(injs["amount"])) is None:
        return False, "Invalid amount"
    if not validate.is_valid_display_name(injs["description"]):
        return False, "Invalid description"

    pay_db = None
    user_db = None
    if "user_id" in injs:
        user_id = injs["user_id"]
        if not isinstance(user_id, int):
            return False, "Missing or invalid data"
    elif "email" in injs:
        if not validate.is_valid_email(injs["email"]):
            return False, "Invalid email address given"
        ok, user_db = sql.sql_select_one("users", {"email": injs["email"]})
        if not ok or not user_db or not len(user_db) or not misc.has_data(user_db, "user_id"):
            return False, f"No user matching '{injs['email']}' could be found"
        user_id = user_db["user_id"]
    else:
        ok, pay_db = find_payment_record(injs)
        if not ok:
            return False, pay_db
        user_id = pay_db["user_id"]

    if user_db is None:
        ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
        if not ok or not user_db or len(user_db) <= 0:
            return False, "Invalid user_id given"

    amount = misc.amt_from_float(amount)
    ok, trans_id = apply_transaction(user_id, amount, "Admin: " + injs["description"], as_admin=True)
    if not ok:
        return False, trans_id

    if pay_db is not None and pay_db["token_type"] == static.PAY_TOKEN_SINGLE:
        sql.sql_delete_one("payments", {"payment_id": pay_db["payment_id"]})

    return True, True


if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("webui")
    print(">>>>>>", apply_transaction(10452, 90000, "Here's some fake money"))
