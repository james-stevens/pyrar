#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" re-create domain actions """

import sys
import json

from librar import mysql
from librar.mysql import sql_server as sql
from librar import static
from librar import misc
from librar import registry
from librar.log import log, init as log_init
from librar.policy import this_policy as policy


def add_domain_action(dom_db, now, when, action):
    print(">>>>> add_domain_action", when, now, (when >= now))
    if when >= now:
        sql.sql_insert("actions", {"domain_id": dom_db["domain_id"], "execute_dt": when, "action": action})


def add_order_reminders(dom_db, now, reminder_sched, reminder_type):
    print(">>>>> add_order_reminders", dom_db["domain_id"],
          sql.sql_exists("orders", {"domain_id": dom_db["domain_id"]}), reminder_sched)
    ok, order_db = sql.sql_select_one("orders", {"domain_id": dom_db["domain_id"]})
    if not ok or len(order_db) <= 0:
        return
    for days in reminder_sched.split(","):
        add_domain_action(dom_db, now, misc.date_add(order_db["created_dt"], days=int(days)), reminder_type)


def domain_actions_live(dom_db, now):
    if dom_db["auto_renew"]:
        add_domain_action(dom_db, now, misc.date_add(dom_db["expiry_dt"],
                                                     days=-1 * policy.policy("auto_renew_before")), "dom/auto-renew")
    else:
        if (reminders_at := policy.policy("renewal_reminders")) is not None:
            for days in reminders_at.split(","):
                add_domain_action(dom_db, misc.date_add(dom_db["expiry_dt"], days=-1 * int(days)), "dom/reminder")

    add_domain_action(dom_db, now, dom_db["expiry_dt"], "dom/expired")

    this_reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    if this_reg is not None:
        add_domain_action(dom_db, now, misc.date_add(dom_db["expiry_dt"], days=this_reg["expire_recover_limit"]),
                          "dom/delete")

    add_order_reminders(dom_db, now, this_reg["renew_order_reminders"], "order/reminder")


def domain_actions_pending_order(dom_db, now):
    if (this_reg := registry.tld_lib.reg_record_for_domain(dom_db["name"])) is None:
        return
    add_domain_action(dom_db, misc.date_add(dom_db["created_dt"], hours=this_reg["new_orders_expire_hrs"]),
                      "order/cancel")
    add_order_reminders(dom_db, now, this_reg["new_order_reminders"], "order/reminder")


def recreate(dom_db, who_did_it="sales"):
    mysql.event_log(
        {
            "event_type": "actions/recreate",
            "notes": f"Recreate domain actions for '{dom_db['name']}', Exp {dom_db['expiry_dt'].split()[0]}",
            "domain_id": dom_db["domain_id"],
            "user_id": dom_db["user_id"],
            "who_did_it": who_did_it,
            "from_where": "localhost"
        }, 1)

    sql.sql_exec(f"delete from actions where domain_id = {dom_db['domain_id']}")

    now = misc.now()
    if dom_db["status_id"] in action_fns:
        return action_fns[dom_db["status_id"]](dom_db, now)

    log(f"WARNINNG: No domain action recreate for domain status {dom_db['status_id']}")
    return True


action_fns = {
    static.STATUS_LIVE: domain_actions_live,
    static.STATUS_WAITING_PAYMENT: domain_actions_pending_order,
    static.STATUS_EXPIRED: domain_actions_live
}


def main():
    log_init(with_debug=True)
    sql.connect("engine")
    registry.start_up()

    ok, dom_db = sql.sql_select_one("domains", {"name": sys.argv[1]})
    if ok and len(dom_db) > 0:
        recreate(dom_db)
        ok, reply = sql.sql_select("actions", {"domain_id": dom_db["domain_id"]}, order_by="execute_dt")
        print(json.dumps(dom_db, indent=3))
        print(json.dumps(reply, indent=3))


if __name__ == "__main__":
    main()
