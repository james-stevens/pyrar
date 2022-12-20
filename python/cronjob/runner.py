#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import argparse

from librar import registry
from librar import sigprocs
from librar import misc
from librar import mysql as sql
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy

COPY_DEL_DOM_COLS = [
    "domain_id", "name", "user_id", "status_id", "auto_renew", "ns", "ds", "client_locks", "created_dt", "amended_dt",
    "expiry_dt"
]


def make_epp_job(job_type,dom_db):
    epp_job = {
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "job_type": job_type,
        "failures": 0,
        "execute_dt": sql.now(),
        "created_dt": None,
        "amended_dt": None
    }

    sql.sql_insert("epp_jobs", epp_job)
    sigprocs.signal_service("backend")



def clear_old_session_keys():
    tout = policy.policy('session_timeout') * 2
    query = f"delete from session_keys where amended_dt < date_sub(now(), interval {tout} minute)"
    return sql.sql_exec(query)


def cancel_unpaid_orders():
    tout = policy.policy('orders_expire_hrs')
    query = f"delete from orders where created_dt < date_sub(now(), interval {tout} hour)"
    sql.sql_exec(query)
    query = (f"delete from domains where status_id = {misc.STATUS_WAITING_PAYMENT} " +
             "and domain_id not in (select domain_id from orders)")
    return sql.sql_exec(query)


def flag_expired_domains():
    query = f"update domains set status_id = {misc.STATUS_EXPIRED} where expiry_dt < now() and status_id = {misc.STATUS_LIVE}"
    return sql.sql_exec(query)


def delete_expired_domains():
    tout = policy.policy('domain_expire_delete')
    ok, doms_db = sql.sql_select("domains", f"expiry_dt < date_sub(now(), interval {tout} day) and status_id = {misc.STATUS_EXPIRED}")
    if not ok:
        return False

    if len(doms_db) <= 0:
        return True

    for dom_db in doms_db:
        log(f"Deleteing expired domain {dom_db['name']}, expired {dom_db['expiry_dt']}")
        del_dom_db = {col: dom_db[col] for col in COPY_DEL_DOM_COLS}
        del_dom_db["deleted_dt"] = None
        sql.sql_insert("deleted_domains", del_dom_db)
        make_epp_job("dom/delete",dom_db)

    ids = [dom_db["domain_id"] for dom_db in doms_db]
    return sql.sql_delete("domains",{"domain_id":ids})


def start_up():
    sql.connect("raradm")
    registry.start_up()


def run_all_jobs():
    clear_old_session_keys()
    cancel_unpaid_orders()
    flag_expired_domains()
    delete_expired_domains()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-D", '--debug', action="store_true")
    args = parser.parse_args()
    log_init(with_debug=args.debug)
    start_up()
    run_all_jobs()
