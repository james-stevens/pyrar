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

clients = None

DEFAULT_NS = ["ns1.example.com", "ns2.exmaple.com"]
JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}


def event_log(notes, epp_job, where):
    event_row = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None,
        "event_type": "EPP-" + epp_job["job_type"],
        "domain_id": epp_job["domain_id"],
        "user_id": 0,
        "who_did_it": "eppsvr",
        "from_where": "localhost",
        "notes": notes
    }
    sql.sql_insert("events", event_row)


def run_epp_request(this_reg, in_json, url=None):
    if url is None:
        url = registry.tld_lib.url(this_reg)

    try:
        resp = clients[this_reg].post(url, json=in_json, headers=misc.HEADER)
        if resp.status_code < 200 or resp.status_code > 299:
            log(f"ERROR: {resp.status_code} {url} {resp.content}", gzz(czz()))
            return None
        ret = json.loads(resp.content)
        return ret
    except Exception as exc:
        log(f"ERROR: XML Request registry '{this_reg}': {exc}", gzz(czz()))
        return None
    return None


def start_up_check():
    for this_reg in clients:
        if run_epp_request(this_reg, {"hello": None}) is None:
            print(f"ERROR: Regisry '{this_reg}' is not working")
            log(f"ERROR: Regisry '{this_reg}' is not working", gzz(czz()))
            sys.exit(0)

    for this_reg in clients:
        if not whois_priv.check_privacy_exists(clients[this_reg], registry.tld_lib.url(this_reg)):
            msg = (f"ERROR: Registry '{this_reg}' " + "privacy record failed to create")
            print(msg)
            log(msg, gzz(czz()))
            sys.exit(1)


def check_dom_data(job_id, domain, ns_list, ds_list):
    if validate.check_domain_name(domain) is not None:
        log(f"EPP-{job_id} Check: '{domain}' failed validation")
        return False

    if len(ns_list) <= 0:
        log(f"EPP-{job_id} Check: No NS given for '{domain}'")
        return False

    for item in ns_list:
        if not validate.is_valid_fqdn(item):
            log(f"EPP-{job_id} '{domain}' NS '{item}' failed validation")
            return False

    for item in ds_list:
        if not validate.is_valid_ds(item):
            log(f"EPP-{job_id} '{domain}' DS '{item}' failed validation")
            return False

    return True


def ds_in_list(ds_data, ds_list):
    for ds_item in ds_list:
        if (ds_item["keyTag"] == ds_data["keyTag"] and ds_item["alg"] == ds_data["alg"]
                and ds_item["digestType"] == ds_data["digestType"] and ds_item["digest"] == ds_data["digest"]):
            return True
    return False


def check_have_data(job_id, dom_db, items):
    for item in items:
        if not sql.has_data(dom_db, item):
            log(f"EPP-{job_id} '{item}' missing or blank", gzz(czz()))
            return False
    return True


def check_num_years(epp_job):
    job_id = epp_job["epp_job_id"]
    if not check_have_data(job_id, epp_job, ["num_years"]):
        return None
    years = int(epp_job["num_years"])
    if years < 1 or years > policy.policy("max_renew_years", 10):
        log(f"EPP-{job_id} num_years failed validation", gzz(czz()))
        return None
    return years


def domain_renew(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    if not check_have_data(job_id, dom_db, ["expiry_dt"]):
        return False
    if not check_have_data(job_id, epp_job, ["num_years"]):
        return False

    if (years := check_num_years(epp_job)) is None:
        return None

    this_reg, url = registry.tld_lib.http_req(name)
    xml = run_epp_request(this_reg, dom_req_xml.domain_renew(name, years, dom_db["expiry_dt"].split()[0]), url)

    if not xml_check_code(job_id, "renew", xml):
        return False

    xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "ren")
    sql.sql_update_one("domains", {"expiry_dt": xml_dom["expiry_dt"]}, {"domain_id": dom_db["domain_id"]})

    return True


def transfer_failed(domain_id):
    sql.sql_update_one("domains", {"status_id": misc.STATUE_TRANS_FAIL}, {"domain_id": domain_id})
    return False


def domain_request_transfer(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None

    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    if not check_have_data(job_id, epp_job, ["num_years", "authcode"]):
        return transfer_failed(dom_db["domain_id"])

    if (years := check_num_years(epp_job)) is None:
        transfer_failed(dom_db["domain_id"])
        return None

    this_reg, url = registry.tld_lib.http_req(name)
    xml = run_epp_request(
        this_reg,
        dom_req_xml.domain_request_transfer(name,
                                            base64.b64decode(epp_job["authcode"]).decode("utf-8"), years), url)

    if not xml_check_code(job_id, "transfer", xml):
        if (epp_job["failures"] + 1) >= policy.policy("epp_retry_attempts", 3):
            return transfer_failed(dom_db["domain_id"])
        return False

    update_cols = {}
    if xml_code == 1000:
        xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "trn")
        update_cols["expiry_dt"] = xml_dom["expiry_dt"]
        update_cols["status_id"] = misc.STATUS_LIVE
        sql.sql_update_one("domains", update_cols, {"domain_id": dom_db["domain_id"]})

    return True


def domain_create(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    ns_list, ds_list = get_domain_lists(dom_db)
    if not check_dom_data(job_id, name, ns_list, ds_list):
        log(f"EPP-{job_id} Domain data failed validation", gzz(czz()))
        return None

    if (years := check_num_years(epp_job)) is None:
        return None

    if len(ns_list) > 0:
        run_host_create(job_id, this_reg, url, ns_list)

    this_reg, url = registry.tld_lib.http_req(name)
    xml = run_epp_request(this_reg, dom_req_xml.domain_create(name, ns_list, ds_list, years), url)
    if not xml_check_code(job_id, "create", xml):
        return False

    xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "cre")

    sql.sql_update_one("domains", {
        "status_id": misc.STATUS_LIVE,
        "reg_create_dt": xml_dom["created_dt"],
        "expiry_dt": xml_dom["expiry_dt"]
    }, {"domain_id": dom_db["domain_id"]})

    return True


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


def epp_get_domain_info(job_id, domain_name):
    this_reg, url = registry.tld_lib.http_req(domain_name)
    if this_reg is None or url is None:
        log(f"EPP-{job_id} '{domain_name}' this_reg or url not given", gzz(czz()))
        return None

    xml = run_epp_request(this_reg, dom_req_xml.domain_info(domain_name), url)

    if not xml_check_code(job_id, "info", xml):
        return None

    return parse_dom_resp.parse_domain_info_xml(xml, "inf")


def get_dom_from_db(epp_job):
    job_id = epp_job["epp_job_id"]
    if not check_have_data(job_id, epp_job, ["domain_id"]):
        log(f"EPP-{job_id} Domain '{domain_id}' missing or invalid", gzz(czz()))
        return None

    domain_id = epp_job["domain_id"]
    ok, dom_db = sql.sql_select_one("domains", {"domain_id": int(domain_id)})
    if not ok:
        log(f"Domain id {domain_id} could not be found", gzz(czz()))
        return None

    name_ok = validate.check_domain_name(dom_db["name"])
    if (not sql.has_data(dom_db, "name")) or (name_ok is not None):
        log(f"EPP-{job_id} For '{domain_id}' domain name missing or invalid ({name_ok})", gzz(czz()))
        return None

    return dom_db


def set_authcode(epp_job):
    job_id = epp_job["epp_job_id"]
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]

    this_reg, url = registry.tld_lib.http_req(name)
    if this_reg is None or url is None:
        log(f"Odd: this_reg or url returned None for '{name}", gzz(czz()))
        return None

    req = dom_req_xml.domain_set_authcode(
        name,
        base64.b64decode(epp_job["authcode"]).decode("utf-8"),
    )

    return xml_check_code(job_id, "info", run_epp_request(this_reg, req, url))


def domain_update_from_db(epp_job):
    job_id = epp_job["epp_job_id"]

    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None

    name = dom_db["name"]
    if (epp_info := epp_get_domain_info(job_id, name)) is None:
        return False

    return do_domain_update(job_id, name, dom_db, epp_info)


def get_domain_lists(dom_db):
    ds_list = []
    ns_list = []
    if sql.has_data(dom_db, "name_servers"):
        ns_list = dom_db["name_servers"].lower().split(",")

    if sql.has_data(dom_db, "ds_recs"):
        ds_list = [validate.frag_ds(item) for item in dom_db["ds_recs"].upper().split(",")]

    return ns_list, ds_list


def run_host_create(job_id, this_reg, url, host_list):
    for host in host_list:
        run_epp_request(this_reg, dom_req_xml.host_add(host), url)


def do_domain_update(job_id, name, dom_db, epp_info):
    this_reg, url = registry.tld_lib.http_req(name)
    ns_list, ds_list = get_domain_lists(dom_db)
    if not check_dom_data(job_id, name, ns_list, ds_list):
        return None

    add_ns = [item for item in ns_list if item not in epp_info["ns"]]
    del_ns = [item for item in epp_info["ns"] if item not in ns_list]

    add_ds = [ds_data for ds_data in ds_list if not ds_in_list(ds_data, epp_info["ds"])]
    del_ds = [ds_data for ds_data in epp_info["ds"] if not ds_in_list(ds_data, ds_list)]

    if (len(add_ns + del_ns + add_ds + del_ds)) <= 0:
        return True

    if len(add_ns) > 0:
        run_host_create(job_id, this_reg, url, add_ns)

    if not sql.has_data(dom_db, "reg_create_dt") or dom_db["reg_create_dt"] != epp_info["created_dt"]:
        sql.sql_update_one("domains", {"reg_create_dt": epp_info["created_dt"]}, {"domain_id": dom_db["domain_id"]})

    update_xml = dom_req_xml.domain_update(name, add_ns, del_ns, add_ds, del_ds)

    return xml_check_code(job_id, "update", run_epp_request(this_reg, update_xml, url))


def xml_check_code(job_id, desc, xml):
    xml_code = xmlapi.xmlcode(xml)
    if xml_code > 1050:
        log(f"EPP-{job_id} XML {desc} request gave {xml_code}", gzz(czz()))
        if xml_code != 9999:
            log(f"EPP-{job_id} {json.dumps(xml)}", gzz(czz()))
        return False

    return True


def job_worked(epp_job):
    sql.sql_delete_one("epp_jobs", {"epp_job_id": epp_job["epp_job_id"]})


def job_abort(epp_job):
    sql.sql_update_one("epp_jobs", {"failures": 9999}, {"epp_job_id": epp_job["epp_job_id"]})


def job_failed(epp_job):
    sql.sql_update_one("epp_jobs", {
        "failures": epp_job["failures"] + 1,
        "execute_dt": sql.now(policy.policy("epp_retry_timeout", 300))
    }, {"epp_job_id": epp_job["epp_job_id"]})


EEP_JOB_FUNC = {
    "dom/update": domain_update_from_db,
    "dom/create": domain_create,
    "dom/renew": domain_renew,
    "dom/transfer": domain_request_transfer,
    "dom/authcode": set_authcode
}


def run_epp_item(epp_job):
    job_id = epp_job["epp_job_id"]
    if (not sql.has_data(epp_job, "job_type") or epp_job["job_type"] not in EEP_JOB_FUNC):
        log(f"EPP-{job_id} Missing or invalid job_type", gzz(czz()))
        return job_abort(epp_job)

    job_run = EEP_JOB_FUNC[epp_job["job_type"]](epp_job)
    notes = (f"{JOB_RESULT[job_run]}: EPP-{job_id} type '{epp_job['job_type']}' " + f"on DOM-{epp_job['domain_id']} " +
             f"retries {epp_job['failures']}/" + f"{policy.policy('epp_retry_attempts', 3)}")

    log(notes, gzz(czz()))
    event_log(notes, epp_job, gzz(czz()))

    if job_run is None:
        return job_abort(epp_job)
    if job_run:
        return job_worked(epp_job)
    return job_failed(epp_job)


def run_server():
    start_up_check()

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

    if args.password is not None:
        print(">>>> SET_AUTH",
              set_authcode({
                  "epp_job_id": "TEST",
                  "domain_id": args.password,
                  "authcode": "eFNaYTlXZ2FVcW8xcmcy"
              }))
        return

    if args.update is not None:
        print(">>>> UPDATE", domain_update_from_db({"epp_job_id": "TEST", "domain_id": args.update}))
        return

    if args.create is not None:
        print(">>> CREATE", domain_create({"epp_job_id": "TEST", "num_years": 1, "domain_id": args.create}))
        return

    if args.renew is not None:
        print(">>> RENEW", domain_renew({"epp_job_id": "TEST", "num_years": 1, "domain_id": args.renew}))
        return

    if args.transfer is not None:
        print(">>> TRANSFER", domain_request_transfer({"epp_job_id": "TEST", "domain_id": args.transfer}))
        return

    if args.info is not None:
        return debug_domain_info(args.info)

    print("No args given")


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
