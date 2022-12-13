#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import argparse
import time
import base64
from inspect import currentframe as czz, getframeinfo as gzz
import httpx

from lib import mysql as sql
from lib import registry
from lib.log import log, debug, init as log_init
from lib.policy import this_policy as policy
from lib import misc
from lib import validate
from lib import parse_dom_resp
import whois_priv
import dom_req_xml
import xmlapi

import epp_module

clients = None

JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}

BACKEND_FUNCS = {"epp": epp_module.BACKEND_JOB_FUNC}


def debug_domain_info(domain):
    if (ret := validate.check_domain_name(domain)) is not None:
        print(">>>> ERROR", ret)
        sys.exit(1)
    xml = dom_req_xml.domain_info(domain)
    this_reg, url = registry.tld_lib.http_req(domain)
    ret = run_epp_request(this_reg, xml, url)
    print(f"\n\n---------- {domain} -----------\n\n")
    print(json.dumps(ret, indent=2))
    if xmlapi.xmlcode(ret) == 1000:
        print(">>>>> PARSER", json.dumps(parse_dom_resp.parse_domain_info_xml(ret, "inf"), indent=4))
    sys.exit(0)


def job_worked(epp_job):
    sql.sql_delete_one("epp_jobs", {"epp_job_id": epp_job["epp_job_id"]})


def job_abort(epp_job):
    sql.sql_update_one("epp_jobs", {"failures": 9999}, {"epp_job_id": epp_job["epp_job_id"]})


def job_failed(epp_job):
    sql.sql_update_one("epp_jobs", {
        "failures": epp_job["failures"] + 1,
        "execute_dt": sql.now(policy.policy("epp_retry_timeout", 300))
    }, {"epp_job_id": epp_job["epp_job_id"]})


def run_epp_item(epp_job):
    job_id = epp_job["epp_job_id"]
    if (not sql.has_data(epp_job, "job_type") or epp_job["job_type"] not in EEP_JOB_FUNC):
        log(f"EPP-{job_id} Missing or invalid job_type", gzz(czz()))
        return job_abort(epp_job)

    job_run = EEP_JOB_FUNC[epp_job["job_type"]](epp_job)
    notes = (f"{JOB_RESULT[job_run]}: EPP-{job_id} type '{epp_job['job_type']}' " + f"on DOM-{epp_job['domain_id']} " +
             f"retries {epp_job['failures']}/" + f"{policy.policy('epp_retry_attempts', 3)}")

    log(notes, gzz(czz()))
    shared.event_log(notes, epp_job, gzz(czz()))

    if job_run is None:
        return job_abort(epp_job)
    if job_run:
        return job_worked(epp_job)
    return job_failed(epp_job)


def run_server():
    for proto, funcs in BACKEND_FUNCS.items():
        if "start_up" in funcs:
            funcs["start_up"]()

    log("EPP-SERVER RUNNING", gzz(czz()))
    while True:
        query = ("select * from epp_jobs where execute_dt <= now()" +
                 f" and failures < {policy.policy('epp_retry_attempts', 3)} limit 1")
        ret, epp_job = sql.run_select(query)
        if ret and len(epp_job) > 0:
            run_epp_item(epp_job[0])
        else:
            time.sleep(5)


def start_up(is_live):
    global clients

    if is_live:
        log_init(policy.policy("facility_eppsvr", 170), with_logging=True)
    else:
        log_init(with_debug=True)

    sql.connect("epprun")
    registry.start_up()
    clients = {p: httpx.Client() for p in registry.tld_lib.ports}


def main():
    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-l", '--live', action="store_true")
    parser.add_argument("-i", '--info', help="Info a domain")
    parser.add_argument("-c", '--create', help="Create a new domain", type=int)
    parser.add_argument("-p", '--password', help="set authcode", type=int)
    parser.add_argument("-u", '--update', help="Update a domain", type=int)
    parser.add_argument("-r", '--renew', help="Renew a domain", type=int)
    parser.add_argument("-t", '--transfer', help="Transfer a domain", type=int)
    args = parser.parse_args()

    start_up(args.live)

    if args.live:
        return run_server()

    for proto, funcs in BACKEND_FUNCS.items():
        if "start_up" in funcs:
            funcs["start_up"]()

    if args.password is not None:
        print(
            ">>>> SET_AUTH",
            epp_module.set_authcode({
                "epp_job_id": "TEST",
                "domain_id": args.password,
                "authcode": "eFNaYTlXZ2FVcW8xcmcy"
            }))
        return

    if args.update is not None:
        print(">>>> UPDATE", epp_module.domain_update_from_db({"epp_job_id": "TEST", "domain_id": args.update}))
        return

    if args.create is not None:
        print(">>> CREATE", epp_module.domain_create({"epp_job_id": "TEST", "num_years": 1, "domain_id": args.create}))
        return

    if args.renew is not None:
        print(">>> RENEW", epp_module.domain_renew({"epp_job_id": "TEST", "num_years": 1, "domain_id": args.renew}))
        return

    if args.transfer is not None:
        print(">>> TRANSFER", epp_module.domain_request_transfer({"epp_job_id": "TEST", "domain_id": args.transfer}))
        return

    if args.info is not None:
        return epp_module.debug_domain_info(args.info)

    print("No args given")


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
