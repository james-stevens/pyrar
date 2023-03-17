#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" Run waiting domain actions when time is ready """

import sys
import argparse

from librar import static, misc, registry, pdns, mysql
from librar.mysql import sql_server as sql
from librar.log import log, debug, init as log_init
from mailer import spool_email
from backend import backend_creator

COPY_DEL_DOM_COLS = [
    "domain_id", "name", "user_id", "status_id", "auto_renew", "ns", "ds", "client_locks", "created_dt", "amended_dt",
    "expiry_dt"
]


def event_log(notes, action):
    mysql.event_log({
        "event_type": "Action:" + action["action"],
        "domain_id": action["domain_id"],
        "user_id": None,
        "who_did_it": "action",
        "from_where": "localhost",
        "notes": notes
    })


def flag_expired_domain(__, dom_db):
    pdns.delete_from_catalog(dom_db["name"])
    sql.sql_update_one("domains", {"status_id": static.STATUS_EXPIRED}, {"domain_id": dom_db["domain_id"]})
    return backend_creator.make_job("dom/expired", dom_db)


def order_cancel(act_db, dom_db):
    sql.sql_delete_one("orders", {"domain_id": dom_db["domain_id"], "user_id": dom_db["user_id"]})
    return delete_domain(act_db, dom_db)


def delete_domain(__, dom_db):
    sql.sql_delete("orders", {"domain_id": dom_db["domain_id"]})
    sql.sql_delete_one("domains", {"domain_id": dom_db["domain_id"]})
    pdns.delete_zone(dom_db["name"])

    if dom_db["status_id"] == static.STATUS_WAITING_PAYMENT:
        del_dom_db = {col: dom_db[col] for col in COPY_DEL_DOM_COLS}
        del_dom_db["deleted_dt"] = None
        sql.sql_insert("deleted_domains", del_dom_db)

    return backend_creator.make_job("dom/delete", dom_db)


def send_order_reminder(act_db, dom_db):
    spool_email.spool("payment_reminder", [["users", {
        "user_id": dom_db["user_id"]
    }], ["orders", {
        "domain_id": dom_db["domain_id"]
    }], ["domains", {
        "domain_id": dom_db["domain_id"]
    }]])
    return True


def auto_renew_domain(act_db, dom_db):
    # CODE REQUIRED
    return True


def send_expiry_reminder(__, dom_db):
    spool_email.spool("reminder", [["users", {
        "user_id": dom_db["user_id"]
    }], ["domains", {
        "domain_id": dom_db["domain_id"]
    }]])
    return True


def delete_action(act_db):
    return sql.sql_delete_one("actions", {"action_id": act_db["action_id"]})


action_exec = {
    "order/cancel": order_cancel,
    "dom/delete": delete_domain,
    "dom/expired": flag_expired_domain,
    "dom/auto-renew": auto_renew_domain,
    "dom/reminder": send_expiry_reminder,
    "order/reminder": send_order_reminder
}


def runner():
    ok, act_data = sql.sql_select("actions", "execute_dt < now()", limit=1, order_by="execute_dt")
    if not ok or not act_data or len(act_data) < 1:
        return False

    act_db = act_data[0]
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


def main():
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-D", '--debug', action="store_true")
    parser.add_argument("-a", '--action')
    parser.add_argument("-d", '--domain')
    args = parser.parse_args()
    log_init(with_debug=(args.debug or args.action or args.domain))

    sql.connect("engine")
    pdns.start_up()
    if args.action and args.domain:
        registry.start_up()
        ok, dom_db = sql.sql_select_one("domains", {"name": args.domain})
        if not ok or len(dom_db) <= 0:
            debug(f"ERROR: {args.domain} not found")
            sys.exit(1)

        if args.action not in action_exec:
            debug(f"ERROR: action '{args.action}' not possible")
            sys.exit(1)

        act_db = {"domain_id": dom_db["domain_id"], "execute_dt": misc.now(), "action": args.action}
        print(">>>> RUNNING", args.action, "on", dom_db["name"])
        print(">>>> ACTION", action_exec[args.action](act_db, dom_db))
        sys.exit(0)

    debug("RUNNING")
    while runner():
        pass


if __name__ == "__main__":
    main()
