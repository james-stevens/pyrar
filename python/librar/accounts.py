#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar.log import log, debug, init as log_init
from librar import mysql as sql
from librar import misc
from librar import sigprocs


def apply_transaction(user_id, amount, desc, as_admin=False):
    set_clauses = [
        "acct_previous_balance = (@prev := acct_current_balance)",
        f"acct_current_balance = (@newbal := acct_current_balance + {amount})",
        "acct_sequence_id = (@trnum := acct_sequence_id + 1)", "amended_dt = now()"
    ]

    where_clauses = [
        f"user_id = {user_id}", "not account_closed", "not acct_on_hold",
        f"(acct_current_balance + {amount}) > acct_overdraw_limit"
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
        return row_count

    if amount > 0:
        sigprocs.signal_service("payeng")

    return row_id


if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("webui")
    print(">>>>>>", apply_transaction(10451, 20000, "Here's some fake money"))
