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
from lib.providers import tld_lib
from lib.log import log, debug, init as log_init
from lib.policy import this_policy as policy
from lib import misc
from lib import validate
import whois_priv
import domxml
import xmlapi

clients = None
MAX_RETRIES = policy.policy("epp_retry_attempts", 3)

DEFAULT_NS = ["ns1.example.com", "ns2.exmaple.com"]
JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}
MAX_NUM_YEARS = policy.policy("max_renew_years", 10)


def event_log(notes, epp_job, where):
    data = {
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
    sql.sql_insert("events", data)


def request_json(prov, in_json, url=None):
    if url is None:
        url = tld_lib.url(prov)

    try:
        resp = clients[prov].post(url, json=in_json, headers=misc.HEADER)
        if resp.status_code < 200 or resp.status_code > 299:
            debug(f">>>>> STATUS: {resp.status_code} {url}", gzz(czz()))
            return None
        ret = json.loads(resp.content)
        return ret
    except Exception as exc:
        log(f"ERROR: XML Request provider '{prov}': {exc}", gzz(czz()))
        return None
    return None


def start_up_check():
    for prov in clients:
        if request_json(prov, {"hello": None}) is None:
            print(f"ERROR: Provider '{prov}' is not working")
            log(f"ERROR: Provider '{prov}' is not working", gzz(czz()))
            sys.exit(0)

    for prov in clients:
        if not whois_priv.check_privacy_exists(clients[prov],
                                               tld_lib.url(prov)):
            print(f"ERROR: Provider '{prov}' privacy record failed to create")
            log(f"ERROR: Provider '{prov}' privacy record failed to create",
                gzz(czz()))
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
        if (ds_item["keyTag"] == ds_data["keyTag"]
                and ds_item["alg"] == ds_data["alg"]
                and ds_item["digestType"] == ds_data["digestType"]
                and ds_item["digest"] == ds_data["digest"]):
            return True
    return False


def check_have_data(job_id, dom_db, items):
    for item in items:
        if not sql.has_data(dom_db, item):
            log(f"EPP-{job_id} '{item}' missing or blank", gzz(czz()))
            return False
    return True


def check_num_years(job_id, dom_db):
    if "num_years" not in dom_db or dom_db["num_years"] == "":
        log(f"EPP-{job_id} num_years missing or blank", gzz(czz()))
        return None
    years = int(dom_db["num_years"])
    if years < 1 or years > MAX_NUM_YEARS:
        log(f"EPP-{job_id} num_years failed validation", gzz(czz()))
        return None
    return years


def domain_renew(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    if not check_have_data(job_id, dom_db, ["num_years", "expiry_dt"]):
        return False

    if (years := check_num_years(dom_db)) is None:
        return None

    prov, url = tld_lib.http_req(name)
    xml = request_json(
        prov, domxml.domain_renew(name, years, dom_db["expiry_dt"].split()[0]),
        url)

    if not xml_check_code(job_id, "renew", xml):
        return False

    data = domxml.parse_domain_xml(xml, "ren")
    sql.sql_update_one("domains", {
        "amended_dt": None,
        "num_years": None,
        "expiry_dt": data["expiry_dt"]
    }, {"domain_id": dom_db["domain_id"]})

    return True


def domain_request_transfer(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    if not check_have_data(job_id, dom_db, ["num_years", "authcode"]):
        return False

    if (years := check_num_years(dom_db)) is None:
        return None

    prov, url = tld_lib.http_req(name)
    xml = request_json(
        prov,
        domxml.domain_request_transfer(name,
                                       base64.b64decode(dom_db["authcode"]),
                                       years), url)

    if not xml_check_code(job_id, "transfer", xml):
        return False

    updt = {"amended_dt": None, "num_years": None}
    if xml_code == 1000:
        data = domxml.parse_domain_xml(xml, "trn")
        updt["expiry_dt"] = data["expiry_dt"]

    sql.sql_update_one("domains", updt, {"domain_id": dom_db["domain_id"]})
    return True


def domain_create(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    ns_list, ds_list = get_domain_lists(dom_db)
    if not check_dom_data(name, ns_list, ds_list):
        log(f"EPP-{job_id} Domain data failed validation", gzz(czz()))
        return None

    if (years := check_num_years(dom_db)) is None:
        return None

    prov, url = tld_lib.http_req(name)
    xml = request_json(prov, domxml.domain_create(name, ns_list, ds_list,
                                                  years), url)
    if not xml_check_code(job_id, "create", xml):
        return False

    data = domxml.parse_domain_xml(xml, "cre")

    sql.sql_update_one(
        "domains", {
            "amended_dt": None,
            "status_id": 10,
            "num_years": None,
            "expiry_dt": data["expiry_dt"]
        }, {"domain_id": dom_db["domain_id"]})

    return True


def debug_one_xml(domain, xml_js, parser=None):
    if (ret := validate.check_domain_name(domain)) is not None:
        print(">>>> ERROR", ret)
        sys.exit(1)
    prov, url = tld_lib.http_req(domain)
    ret = request_json(prov, xml_js, url)
    print(f"\n\n---------- {domain} -----------\n\n")
    print(json.dumps(ret, indent=2))
    if xmlapi.xmlcode(ret) == 1000 and parser is not None:
        print(">>>>> PARSER", json.dumps(parser(ret), indent=4))
    sys.exit(0)


def test_domain_info(domain):
    return debug_one_xml(domain, domxml.domain_info(domain),
                         domxml.parse_domain_xml)


def epp_get_domain_info(job_id, domain_name):
    prov, url = tld_lib.http_req(domain_name)
    if prov is None or url is None:
        log(f"EPP-{job_id} '{domain_name}' prov or url not given", gzz(czz()))
        return None

    xml = request_json(prov, domxml.domain_info(domain_name), url)

    if not xml_check_code(job_id, "info", xml):
        return None

    return domxml.parse_domain_xml(xml, "inf")


def get_dom_from_db(epp_job):
    job_id = epp_job["epp_job_id"]
    if not check_have_data(job_id, epp_job, ["domain_id"]):
        log(f"EPP-{job_id} Domain '{domain_id}' missing or invalid",
            gzz(czz()))
        return None

    domain_id = epp_job["domain_id"]
    ret, dom_db = sql.sql_select_one("domains", {"domain_id": int(domain_id)})
    if not ret:
        log(f"Domain id {domain_id} could not be found", gzz(czz()))
        return None

    if not sql.has_data(dom_db, "name") or validate.check_domain_name(
            dom_db["name"]) is not None:
        log(f"EPP-{job_id} For '{domain_id}' domain name missing or invalid",
            gzz(czz()))
        return None

    return dom_db


def set_authcode(epp_job):
    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None
    name = dom_db["name"]

    prov, url = tld_lib.http_req(name)
    if prov is None or url is None:
        log(f"Odd: prov or url returned None for '{name}", gzz(czz()))
        return None

    req = domxml.domain_set_authcode(name,
                                     base64.b64decode(dom_db["authcode"]))

    return xml_check_code(job_id, "info", request_json(prov, req, url))


def domain_update_from_db(epp_job):
    job_id = epp_job["epp_job_id"]

    if (dom_db := get_dom_from_db(epp_job)) is None:
        return None

    name = dom_db["name"]
    if (epp_info := epp_get_domain_info(job_id, name)) is None:
        return False

    return do_domain_update(job_id, name, dom_db, epp_info)


def get_domain_lists(dom_db):
    ns_list = dom_db["name_servers"].split(",") if sql.has_data(
        dom_db, "name_servers") else []

    ds_list = [
        validate.frag_ds(item) for item in dom_db["ds_recs"].split(",")
    ] if sql.has_data(dom_db, "ds_recs") else []

    return ns_list, ds_list


def do_domain_update(job_id, name, dom_db, epp_info):
    prov, url = tld_lib.http_req(name)
    ns_list, ds_list = get_domain_lists(dom_db)
    if not check_dom_data(job_id, name, ns_list, ds_list):
        return None

    add_ns = [item for item in ns_list if item not in epp_info["ns"]]
    del_ns = [item for item in epp_info["ns"] if item not in ns_list]

    add_ds = [
        ds_data for ds_data in ds_list
        if not ds_in_list(ds_data, epp_info["ds"])
    ]

    del_ds = [
        ds_data for ds_data in epp_info["ds"]
        if not ds_in_list(ds_data, ds_list)
    ]

    if (len(add_ns + del_ns + add_ds + del_ds)) <= 0:
        return True

    update_xml = domxml.domain_update(name, add_ns, del_ns, add_ds, del_ds)

    return xml_check_code(job_id, "update",
                          request_json(prov, update_xml, url))


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
    sql.sql_update_one("epp_jobs", {
        "amended_dt": None,
        "failures": 9999
    }, {"epp_job_id": epp_job["epp_job_id"]})


def job_failed(epp_job):
    sql.sql_update_one(
        "epp_jobs", {
            "amended_dt": None,
            "failures": epp_job["failures"] + 1,
            "execute_dt": sql.now(60)
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
    if (not sql.has_data(epp_job, "job_type")
            or epp_job["job_type"] not in EEP_JOB_FUNC):
        log(f"EPP-{job_id} Missing or invalid job_type", gzz(czz()))
        return job_abort(epp_job)

    job_run = EEP_JOB_FUNC[epp_job["job_type"]](epp_job)
    notes = (
        f"{JOB_RESULT[job_run]}: EPP-{job_id} type '{epp_job['job_type']}' " +
        f"on DOM-{epp_job['domain_id']} " +
        f"retries {epp_job['failures']}/{MAX_RETRIES}")

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
                 f" and failures < {MAX_RETRIES} limit 1")
        ret, data = sql.run_select(query)
        if ret and len(data) > 0:
            run_epp_item(data[0])
        else:
            time.sleep(5)


def main():
    global clients

    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-l", '--live', action="store_true")
    parser.add_argument("-i", '--info', help="Info a domain")
    parser.add_argument("-c", '--create', help="Create a new domain", type=int)
    parser.add_argument("-p", '--password', help="set authcode", type=int)
    parser.add_argument("-u", '--update', help="Update a domain", type=int)
    parser.add_argument("-n", '--renew', help="Renew a domain", type=int)
    parser.add_argument("-t", '--transfer', help="Transfer a domain", type=int)
    args = parser.parse_args()

    clients = {p: httpx.Client() for p in tld_lib.ports}
    sql.connect("epprun")

    if args.live:
        log_init(policy.policy("facility_eppsvr", 170), with_logging=True)
        return run_server()

    log_init(policy.policy("facility_eppsvr", 170),
             debug=True,
             with_logging=True)

    if args.password is not None:
        print(">>>> SET_AUTH",
              set_authcode({
                  "epp_job_id": "TEST",
                  "domain_id": args.password
              }))
        return

    if args.update is not None:
        print(
            ">>>> UPDATE",
            domain_update_from_db({
                "epp_job_id": "TEST",
                "domain_id": args.update
            }))
        return

    if args.create is not None:
        print(">>> CREATE",
              domain_create({
                  "epp_job_id": "TEST",
                  "domain_id": args.create
              }))
        return

    if args.renew is not None:
        print(">>> CREATE",
              domain_renew({
                  "epp_job_id": "TEST",
                  "domain_id": args.renew
              }))
        return

    if args.transfer is not None:
        print(
            ">>> TRANSFER",
            domain_request_transfer({
                "epp_job_id": "TEST",
                "domain_id": args.transfer
            }))
        return

    if args.info is not None:
        return test_domain_info(args.info)

    print("No args given")


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
