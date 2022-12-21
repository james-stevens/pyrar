#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json

from librar import mysql as sql
from librar import misc
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy


def add_delete_action(dom_db, which_policy):
    sql.sql_insert(
        "actions", {
            "domain_id": dom_db["domain_id"],
            "execute_dt": sql.date_add(dom_db["expiry_dt"], days=policy.policy(which_policy)),
            "action": "dom/delete"
        })


def domain_actions_live(dom_db):
    sql.sql_insert("actions", {
        "domain_id": dom_db["domain_id"],
        "execute_dt": dom_db["expiry_dt"],
        "action": "dom/expired"
    })
    add_delete_action(dom_db, "domain_expire_delete")
    if dom_db["auto_renew"]:
        sql.sql_insert(
            "actions", {
                "domain_id": dom_db["domain_id"],
                "execute_dt": sql.date_add(dom_db["expiry_dt"], days=-1 * policy.policy("auto_renew_before")),
                "action": "dom/auto-renew"
            })
    else:
        if (reminders_at := policy.policy("renewal_reminders")) is not None:
            for days in reminders_at.split(","):
                sql.sql_insert(
                    "actions", {
                        "domain_id": dom_db["domain_id"],
                        "execute_dt": sql.date_add(dom_db["expiry_dt"], days=-1 * int(days)),
                        "action": "dom/reminder"
                    })


def domain_actions_pending_order(dom_db):
    add_delete_action(dom_db, 'orders_expire_hrs')


def recreate_domain_actions(dom_db):
    sql.sql_exec(f"delete from actions where domain_id = {dom_db['domain_id']}")
    if dom_db["status_id"] in action_fns:
        return action_fns[dom_db["status_id"]](dom_db)
    return True


action_fns = {misc.STATUS_LIVE: domain_actions_live, misc.STATUS_WAITING_PAYMENT: domain_actions_pending_order}

if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("epprun")
    ok, dom_db = sql.sql_select_one("domains", {"name": sys.argv[1]})
    if ok:
        recreate_domain_actions(dom_db)
        ok, reply = sql.sql_select("actions", {"domain_id": dom_db["domain_id"]}, order_by="execute_dt")
        print(json.dumps(dom_db, indent=3))
        print(json.dumps(reply, indent=3))
