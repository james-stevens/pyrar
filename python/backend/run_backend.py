#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" run job requests queued in table `backend` """

import sys
import json
import argparse

from librar import mysql as sql
from librar import registry
from librar import pdns
from librar import domobj
from librar.log import log, init as log_init
from librar.policy import this_policy as policy
from librar import sigprocs
from actions import creator

from backend import shared

# pylint: disable=unused-wildcard-import, wildcard-import
from backend import dom_handler
from backend.dom_plugins import *

JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}

# dom/update included here in case dom.auto_renew changes
RECREATE_ACTIONS_FOR = ["dom/update", "dom/renew", "dom/create", "dom/transfer", "dom/recover"]


def job_worked(bke_job):
    """ job worked """
    sql.sql_delete_one("backend", {"backend_id": bke_job["backend_id"]})


def job_abort(bke_job):
    """ job should not be retried """
    sql.sql_update_one("backend", {"failures": 9999}, {"backend_id": bke_job["backend_id"]})


def job_failed(bke_job):
    """ job failed, but should be retried """
    sql.sql_update_one("backend", {
        "failures": bke_job["failures"] + 1,
        "execute_dt": sql.now(policy.policy("backend_retry_timeout"))
    }, {"backend_id": bke_job["backend_id"]})


def post_processing(bke_job):
    """ job worked, but there's more to do """
    ok, dom_db = sql.sql_select_one("domains", {"domain_id": bke_job["domain_id"]})
    if not ok:
        log(f"ERROR: Failed to run post-processing for {bke_job['job_type']} on missing domain {bke_job['domain_id']}")
        return False

    if bke_job["job_type"] == "dom/create":
        pdns.delete_zone(dom_db["name"])

    if bke_job["job_type"] in RECREATE_ACTIONS_FOR:
        creator.recreate_domain_actions(dom_db)

    return True


def run_backend_item(bke_job):
    """ run a backend job """
    job_id = bke_job["backend_id"]
    dom = domobj.Domain()
    if not dom.set_by_id(bke_job["domain_id"]):
        return job_abort(bke_job)

    if sql.has_data(bke_job, "user_id") and bke_job["job_type"] != "dom/transfer":
        if bke_job["user_id"] != dom.dom_db["user_id"]:
            log(f"BKE-{job_id}: Domain '{dom.dom_db['name']}' is not owned by '{bke_job['user_id']}'")
            return job_abort(bke_job)

    reg = registry.tld_lib.reg_record_for_domain(dom.dom_db["name"])
    if reg["type"] not in dom_handler.backend_plugins:
        return job_abort(bke_job)

    if (plugin_func := dom_handler.run(reg["type"], bke_job["job_type"])) is None:
        log(f"BKE-{job_id}: Missing or invalid job_type for '{reg['type']}'")
        return job_abort(bke_job)

    job_run = plugin_func(bke_job, dom.dom_db)

    notes = (f"{JOB_RESULT[job_run]}: BKE-{job_id} type '{reg['type']}:{bke_job['job_type']}' " +
             f"on DOM-{bke_job['domain_id']} retries {bke_job['failures']}/" +
             f"{policy.policy('backend_retry_attempts')}")

    log(notes)
    shared.event_log(notes, bke_job)

    if job_run is None:
        return job_abort(bke_job)
    if job_run:
        post_processing(bke_job)
        return job_worked(bke_job)

    return job_failed(bke_job)


def run_server():
    """ continuously run the backend processing """
    log("BACK-END SERVER RUNNING")
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
    """ run the plug-in's start-up fns """
    if is_live:
        log_init(policy.policy("facility_backend"), with_logging=True)
    else:
        log_init(with_debug=True)

    sql.connect("engine")
    registry.start_up()

    all_regs = registry.tld_lib.regs_file.data()
    have_types = {reg_data["type"]: True for __, reg_data in all_regs.items() if "type" in reg_data}
    for this_type, funcs in dom_handler.backend_plugins.items():
        if this_type in have_types and "start_up" in funcs:
            funcs["start_up"]()


def main():
    """ main """
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-l", '--live', action="store_true")
    parser.add_argument("-D", '--debug', action="store_true")
    parser.add_argument("-s", '--start-up', action="store_true")
    parser.add_argument("-a", '--action', help="Plugin action")
    parser.add_argument("-d", '--domain', help="Plugin name")
    args = parser.parse_args()

    if args.debug:
        start_up(False)
        return run_server()

    if args.live:
        start_up(True)
        return run_server()

    if args.start_up:
        start_up(args.live)
        sys.exit(1)

    if not args.action or not args.domain:
        print("Plugin or action or domain not specified")
        sys.exit(1)

    start_up(args.live)

    dom = domobj.Domain()
    if args.domain.isdecimal():
        ok, reply = dom.set_by_id(int(args.domain))
    else:
        ok, reply = dom.load_name(args.domain)

    if not ok:
        print("ERROR",reply)
        sys.exit(1)

    bke_job = {
        "backend_id": "TEST",
        "authcode": "eFNaYTlXZ2FVcW8xcmcy",
        "job_type": args.action,
        "num_years": 1,
        "domain_id": dom.dom_db["domain_id"]
    }

    this_handler = dom_handler.backend_plugins[dom.registry["type"]]
    if args.action not in this_handler:
        print(f"Action '{args.action}' not supported by Plugin '{dom.registry['type']}'")
        sys.exit(1)

    print(f"Running {dom.registry['type']}:{args.action} on {dom.dom_db['name']}")
    out_js = this_handler[args.action](bke_job, dom.dom_db)
    print(json.dumps(out_js, indent=3))
    return 0


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
