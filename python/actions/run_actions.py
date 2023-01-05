#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import argparse
import inspect

from librar import mysql as sql
from librar import misc
from librar import sigprocs
from librar.log import log, debug, init as log_init

COPY_DEL_DOM_COLS = [
    "domain_id", "name", "user_id", "status_id", "auto_renew", "ns", "ds", "client_locks", "created_dt", "amended_dt",
    "expiry_dt"
]


def event_log(notes, action):
    where = inspect.stack()[1]
    event_row = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None,
        "event_type": "Action:" + action["action"],
        "domain_id": action["domain_id"],
        "user_id": None,
        "who_did_it": "action",
        "from_where": "localhost",
        "notes": notes
    }
    sql.sql_insert("events", event_row)


def make_backend_job(job_type, dom_db):
    backend = {
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "job_type": job_type,
        "failures": 0,
        "execute_dt": sql.now(),
        "created_dt": None,
        "amended_dt": None
    }

    ok = sql.sql_insert("backend", backend)
    sigprocs.signal_service("backend")
    return ok


def flag_expired_domain(act_db, dom_db):
    sql.sql_update_one("domains", {"status_id": misc.STATUS_EXPIRED}, {"domain_id": dom_db["domain_id"]})
    return make_backend_job("dom/expired", dom_db)


def order_cancel(act_db, dom_db):
    sql.sql_delete_one("orders",{"domain_id":dom_db["domain_id"],"user_id":dom_db["user_id"]})
    return delete_domain(act_db, dom_db)


def delete_domain(act_db, dom_db):
    ok = sql.sql_delete_one("domains", {"domain_id": dom_db["domain_id"]})
    if not ok:
        return False

    ok_pdns = pdns.delete_zone(dom_db["name"])

    if dom_db["status_id"] == misc.STATUS_WAITING_PAYMENT:
        del_dom_db = {col: dom_db[col] for col in COPY_DEL_DOM_COLS}
        del_dom_db["deleted_dt"] = None
        sql.sql_insert("deleted_domains", del_dom_db)

    return make_backend_job("dom/delete", dom_db)


def auto_renew_domain(act_db, dom_db):
    # CODE REQUIRED
    return True


def send_expiry_reminder(act_db, dom_db):
    # CODE REQUIRED
    return True


def delete_action(act_db):
    sql.sql_delete_one("actions", {"action_id": act_db["action_id"]})
    return True


action_exec = {
    "order/cancel": order_cancel,
    "dom/delete": delete_domain,
    "dom/expired": flag_expired_domain,
    "dom/auto-renew": auto_renew_domain,
    "dom/reminder": send_expiry_reminder
}


def runner():
    ok, act_db = sql.sql_select("actions", f"execute_dt < now()", limit=1, order_by="execute_dt")
    if not ok or len(act_db) < 1:
        return False

    act_db = act_db[0]
    if act_db["action"] not in action_exec:
        log(f"ERROR: Domain action '{act_db['action']}' for DOM-{act_db['domain_id']} - action not found")
        return delete_action(act_db)

    ok, dom_db = sql.sql_select_one("domains", {"domain_id": act_db["domain_id"]})
    if not ok or len(dom_db) < 1:
        log(f"ERROR: Domain action '{act_db['action']}' for DOM-{act_db['domain_id']} - domain not found")
        return delete_action(act_db)

    if not action_exec[act_db["action"]](act_db, dom_db):
        log(f"ERROR: Domain action '{act_db['action']}' for DOM-{dom_db['domain_id']} - action failed")

    event_log(f"Domain action '{act_db['action']}' for DOM-{dom_db['domain_id']} - action done", act_db)
    return delete_action(act_db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-D", '--debug', action="store_true")
    parser.add_argument("-a", '--action')
    parser.add_argument("-d", '--domain')
    args = parser.parse_args()
    log_init(with_debug=(args.debug or args.action or args.domain))

    sql.connect("engine")
    if args.action and args.domain:
        ok, dom_db = sql.sql_select_one("domains", {"name": args.domain})
        if not ok or len(dom_db) <= 0:
            debug(f"ERROR: {args.domain} not found")
            sys.exit(1)

        if args.action not in action_exec:
            debug(f"ERROR: action '{args.action}' not possible")
            sys.exit(1)

        act_db = {"domain_id": dom_db["domain_id"], "execute_dt": sql.now(), "action": args.action}
        print(">>>> RUNNING", args.action, "on", dom_db["name"])
        print(">>>> ACTION", action_exec[args.action](act_db, dom_db))
        sys.exit(0)

    debug("RUNNING")
    while runner():
        pass
