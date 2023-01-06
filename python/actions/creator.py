#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import inspect

from librar import mysql as sql
from librar import misc
from librar import registry
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy


def add_domain_action(dom_db,when,action):
    sql.sql_insert(
        "actions", {
            "domain_id": dom_db["domain_id"],
            "execute_dt": when,
            "action": action
        })


def domain_actions_live(dom_db):
    if dom_db["auto_renew"]:
        add_domain_action(dom_db,sql.date_add(dom_db["expiry_dt"], days=-1 * policy.policy("auto_renew_before")),"dom/auto-renew")
    else:
        if (reminders_at := policy.policy("renewal_reminders")) is not None:
            for days in reminders_at.split(","):
                add_domain_action(dom_db,sql.date_add(dom_db["expiry_dt"], days=-1 * int(days)),"dom/reminder")

    this_reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    add_domain_action(dom_db,dom_db["expiry_dt"],"dom/expired")
    add_domain_action(dom_db,sql.date_add(dom_db["expiry_dt"], days=this_reg["expire_recover_limit"]),"dom/delete")


def domain_actions_pending_order(dom_db):
    add_domain_action(dom_db,sql.date_add(dom_db["created_dt"], hours=this_reg["orders_expire_hrs"]),"order/cancel")


def recreate_domain_actions(dom_db):
    where = inspect.stack()[1]
    event_db = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None,
        "event_type": "actions/recreate",
        "notes": f"Recreate domain actions for '{dom_db['name']}', Exp {dom_db['expiry_dt']}",
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "who_did_it": "sales",
        "from_where": "localhost"
    }
    sql.sql_insert("events", event_db)

    sql.sql_exec(f"delete from actions where domain_id = {dom_db['domain_id']}")

    if dom_db["status_id"] in action_fns:
        return action_fns[dom_db["status_id"]](dom_db)
    else:
        log(f"WARNINNG: No domain action recreate for domain status {dom_db['status_id']}")

    return True


action_fns = {misc.STATUS_LIVE: domain_actions_live, misc.STATUS_WAITING_PAYMENT: domain_actions_pending_order}

if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("engine")
    registry.start_up()

    ok, dom_db = sql.sql_select_one("domains", {"name": sys.argv[1]})
    if ok and len(dom_db)>0:
        recreate_domain_actions(dom_db)
        ok, reply = sql.sql_select("actions", {"domain_id": dom_db["domain_id"]}, order_by="execute_dt")
        print(json.dumps(dom_db, indent=3))
        print(json.dumps(reply, indent=3))
