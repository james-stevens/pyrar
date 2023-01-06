#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import argparse

from librar import mysql as sql
from librar import registry
from librar.log import log, init as log_init
from librar.policy import this_policy as policy
from librar import sigprocs
from actions import creator

from backend import shared

# pylint: disable=unused-wildcard-import, wildcard-import
from backend import handler
from backend.plugins import *

JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}

# dom/update included here in case dom.auto_renew changes
RECREATE_ACTIONS_FOR = ["dom/update", "dom/renew", "dom/create", "dom/transfer", "dom/recover"]


def job_worked(bke_job):
    sql.sql_delete_one("backend", {"backend_id": bke_job["backend_id"]})


def job_abort(bke_job):
    sql.sql_update_one("backend", {"failures": 9999}, {"backend_id": bke_job["backend_id"]})


def job_failed(bke_job):
    sql.sql_update_one("backend", {
        "failures": bke_job["failures"] + 1,
        "execute_dt": sql.now(policy.policy("backend_retry_timeout"))
    }, {"backend_id": bke_job["backend_id"]})


def check_for_recreate(bke_job):
    if bke_job["job_type"] not in RECREATE_ACTIONS_FOR:
        return True

    ok, dom_db = sql.sql_select_one("domains", {"domain_id": bke_job["domain_id"]})
    if not ok:
        log(f"ERROR: trying to create actions for missing domain {bke_job['domain_id']}")
        return False

    return creator.recreate_domain_actions(dom_db)


def run_backend_item(bke_job):
    job_id = bke_job["backend_id"]
    if (dom_db := shared.get_dom_from_db(bke_job)) is None:
        return job_abort(bke_job)

    if sql.has_data(bke_job, "user_id") and bke_job["job_type"] != "dom/transfer":
        if bke_job["user_id"] != dom_db["user_id"]:
            log(f"EPP-{job_id}: Domain '{dom_db['name']}' is not owned by '{bke_job['user_id']}'")
            return job_abort(bke_job)

    reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    if reg["type"] not in handler.backend_plugins:
        return job_abort(bke_job)

    if (plugin_func := handler.run(reg["type"], bke_job["job_type"])) is None:
        log(f"EPP-{job_id}: Missing or invalid job_type for '{reg['type']}'")
        return job_abort(bke_job)

    job_run = plugin_func(bke_job, dom_db)

    notes = (f"{JOB_RESULT[job_run]}: EPP-{job_id} type '{reg['type']}:{bke_job['job_type']}' " +
             f"on DOM-{bke_job['domain_id']} retries {bke_job['failures']}/" +
             f"{policy.policy('backend_retry_attempts')}")

    log(notes)
    shared.event_log(notes, bke_job)

    if job_run is None:
        return job_abort(bke_job)
    if job_run:
        check_for_recreate(bke_job)
        return job_worked(bke_job)

    return job_failed(bke_job)


def run_server():
    log("EPP-SERVER RUNNING")
    signal_mtime = None
    while True:
        query = ("select * from backend where execute_dt <= now()" +
                 f" and failures < {policy.policy('backend_retry_attempts')} order by backend_id limit 1")
        ret, bke_job = sql.run_select(query)
        if ret and len(bke_job) > 0:
            run_backend_item(bke_job[0])
        else:
            signal_mtime = sigprocs.signal_wait("backend", signal_mtime)


def start_up(is_live):
    if is_live:
        log_init(policy.policy("facility_backend"), with_logging=True)
    else:
        log_init(with_debug=True)

    sql.connect("engine")
    registry.start_up()

    for __, funcs in handler.backend_plugins.items():
        if "start_up" in funcs:
            funcs["start_up"]()


def main():
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-l", '--live', action="store_true")
    parser.add_argument("-D", '--debug', action="store_true")
    parser.add_argument("-s", '--start-up', action="store_true")
    parser.add_argument("-a", '--action', help="Plugin action")
    parser.add_argument("-p", '--plugin', help="Plugin name")
    parser.add_argument("-d", '--domain-id', help="Plugin name", type=int)
    args = parser.parse_args()

    if args.debug:
        start_up(False)
        return run_server()

    if args.live:
        start_up(True)
        return run_server()

    if args.plugin and args.start_up:
        start_up(args.live)
        sys.exit(1)

    if not args.plugin or not args.action or not args.domain_id:
        print("Plugin or action or domain_id not specified")
        sys.exit(1)

    if args.plugin not in handler.backend_plugins:
        print(f"Plugin '{args.plugin}' not supported")
        sys.exit(1)

    if args.action not in handler.backend_plugins[args.plugin]:
        print(f"Action '{args.action}' not supported by Plugin '{args.plugin}'")
        sys.exit(1)

    start_up(args.live)

    this_fn = handler.backend_plugins[args.plugin][args.action]
    bke_job = {
        "backend_id": "TEST",
        "authcode": "eFNaYTlXZ2FVcW8xcmcy",
        "job_type": args.action,
        "num_years": 1,
        "domain_id": args.domain_id
    }
    dom_db = shared.get_dom_from_db(bke_job)
    out_js = this_fn(bke_job, dom_db)
    print(json.dumps(out_js, indent=3))
    return 0


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
