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

RECREATE_ACTIONS_FOR = [ "dom/renew", "dom/create", "dom/transfer", "dom/recover" ]


def job_worked(epp_job):
    sql.sql_delete_one("epp_jobs", {"epp_job_id": epp_job["epp_job_id"]})


def job_abort(epp_job):
    sql.sql_update_one("epp_jobs", {"failures": 9999}, {"epp_job_id": epp_job["epp_job_id"]})


def job_failed(epp_job):
    sql.sql_update_one("epp_jobs", {
        "failures": epp_job["failures"] + 1,
        "execute_dt": sql.now(policy.policy("epp_retry_timeout"))
    }, {"epp_job_id": epp_job["epp_job_id"]})


def check_for_recreate(epp_job):
    if epp_job["job_type"] not in RECREATE_ACTIONS_FOR:
        return True

    ok, dom_db = sql.sql_select_one("domains", {"domain_id":epp_job["domain_id"]})
    if not ok:
        log(f"ERROR: trying to create actions for missing domain {epp_job['domain_id']}")
        return False

    return creator.recreate_domain_actions(dom_db)


def run_epp_item(epp_job):
    job_id = epp_job["epp_job_id"]
    if (dom_db := shared.get_dom_from_db(epp_job)) is None:
        return job_abort(epp_job)

    if sql.has_data(epp_job, "user_id") and epp_job["job_type"] != "dom/transfer":
        if epp_job["user_id"] != dom_db["user_id"]:
            log(f"EPP-{job_id}: Domain '{dom_db['name']}' is not owned by '{epp_job['user_id']}'")
            return job_abort(epp_job)

    reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    if reg["type"] not in handler.backend_plugins:
        return job_abort(epp_job)

    if (plugin_func := handler.run(reg["type"],epp_job["job_type"])) is None:
        log(f"EPP-{job_id}: Missing or invalid job_type for '{reg['type']}'")
        return job_abort(epp_job)

    job_run = plugin_func(epp_job, dom_db)
    notes = (f"{JOB_RESULT[job_run]}: EPP-{job_id} type '{reg['type']}:{epp_job['job_type']}' " +
             f"on DOM-{epp_job['domain_id']} retries {epp_job['failures']}/" +
             f"{policy.policy('epp_retry_attempts')}")

    log(notes)
    shared.event_log(notes, epp_job)

    if job_run is None:
        return job_abort(epp_job)
    if job_run:
        check_for_recreate(epp_job)
        return job_worked(epp_job)

    return job_failed(epp_job)


def run_server():
    log("EPP-SERVER RUNNING")
    signal_mtime = None
    while True:
        query = ("select * from epp_jobs where execute_dt <= now()" +
                 f" and failures < {policy.policy('epp_retry_attempts')} order by epp_job_id limit 1")
        ret, epp_job = sql.run_select(query)
        if ret and len(epp_job) > 0:
            run_epp_item(epp_job[0])
        else:
            signal_mtime = sigprocs.signal_wait("backend",signal_mtime)


def start_up(is_live):
    if is_live:
        log_init(policy.policy("facility_eppsvr"), with_logging=True)
    else:
        log_init(with_debug=True)

    sql.connect("epprun")
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
    epp_job = {
        "epp_job_id": "TEST",
        "authcode": "eFNaYTlXZ2FVcW8xcmcy",
        "job_type": args.action,
        "num_years": 1,
        "domain_id": args.domain_id
        }
    dom_db = shared.get_dom_from_db(epp_job)
    out_js = this_fn(epp_job,dom_db)
    print(json.dumps(out_js, indent=3))
    return 0


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
