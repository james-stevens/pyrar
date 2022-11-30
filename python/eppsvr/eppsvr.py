#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import argparse
import time
from inspect import currentframe as czz, getframeinfo as gzz
import httpx

from lib import mysql as sql
from lib.providers import tld_lib
from lib.log import log, debug, init as log_init
from lib.policy import this_policy as policy
from lib import api
from lib import validate
import whois_priv
import domxml
import xmlapi

clients = None
max_retries = policy.policy("epp_retry_attempts", 3)

DEFAULT_NS = ["ns1.example.com", "ns2.exmaple.com"]


def request_json(prov, in_json, url=None):
    if url is None:
        url = tld_lib.url(prov)

    try:
        resp = clients[prov].post(url, json=in_json, headers=api.HEADER)
        if resp.status_code < 200 or resp.status_code > 299:
            debug(">>>>> STATUS: {resp.status_code} {url}", gzz(czz()))
            return None
        ret = json.loads(resp.content)
        return ret
    except Exception as exc:
        debug(">>>>> Exception {exc}", gzz(czz()))
        return None
    return None


def start_up_check():
    for prov in clients:
        if request_json(prov, {"hello": None}) is None:
            log(f"ERROR: Provider '{prov}' is not working", gzz(czz()))
            sys.exit(0)

    for prov in clients:
        if not whois_priv.check_privacy_exists(clients[prov],
                                               tld_lib.url(prov)):
            log(f"ERROR: Provider '{prov}' privacy record failed to create",
                gzz(czz()))
            sys.exit(1)


def check_dom_data(domain, data_list, validate_func):
    if validate.check_domain_name(domain) is not None:
        log(f"Check: '{domain}' failed validation")
        return False

    if len(data_list) <= 0:
        log(f"Check: No NS given for '{domain}'")
        return False

    for item in data_list:
        if not validate_func(item):
            log(f"Check: '{domain}' - data item '{item}' failed validation")
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


def domain_create(domain, ns_list, years):
    if not check_dom_data(domain, ns_list, validate.is_valid_fqdn):
        return None

    if years < 1 or years > policy.policy("max_renew_years", 10):
        return None

    prov, url = tld_lib.http_req(domain)
    ret = request_json(prov, domxml.domain_create(domain, ns_list, years), url)
    return xmlapi.xmlcode(ret) == 1000


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
                         domxml.parse_domain_info)


def epp_get_domain_info(domain_name):
    prov, url = tld_lib.http_req(domain_name)
    if prov is None or url is None:
        return None
    xml = request_json(prov, domxml.domain_info(domain_name), url)
    if xmlapi.xmlcode(xml) != 1000:
        return None
    return domxml.parse_domain_info(xml)


def update_domain_from_db(epp_job):
    if not sql.has_data(epp_job, "domain_id"):
        return None

    domain_id = epp_job["domain_id"]
    ret, dom_db = sql.sql_select_one("domains", {"domain_id": domain_id})
    if not ret:
        log(f"Domain id {domain_id} could not be found", gzz(czz()))
        return None

    if not sql.has_data(dom_db, "name") or validate.check_domain_name(
            dom_db["name"]) is not None:
        log(f"EPP[{domain_id}]: Domain name missing or invalid", gzz(czz()))
        return None

    name = dom_db["name"]

    prov, url = tld_lib.http_req(name)
    if prov is None or url is None:
        log(f"Odd: prov or url returned None for '{dom_db['name']}",
            gzz(czz()))
        return None

    xml = request_json(prov, domxml.domain_info(name), url)
    if xmlapi.xmlcode(xml) != 1000:
        return False

    epp_info = domxml.parse_domain_info(xml)

    return do_domain_update(name, dom_db, epp_info, prov, url)


def do_domain_update(name, dom_db, epp_info, prov, url):

    ns_list = dom_db["name_servers"].split(",") if sql.has_data(
        dom_db, "name_servers") else []
    add_ns = [item for item in ns_list if item not in epp_info["ns"]]
    del_ns = [item for item in epp_info["ns"] if item not in ns_list]

    ds_list = [
        validate.frag_ds(item) for item in dom_db["ds_recs"].split(",")
    ] if sql.has_data(dom_db, "ds_recs") else []

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
    update_ret = request_json(prov, update_xml, url)

    return xmlapi.xmlcode(update_ret) == 1000


def job_worked(epp_job):
    sql.sql_delete_one("epp_jobs", {"epp_job_id": epp_job["epp_job_id"]})


def job_abort(epp_job):
    sql.sql_update_one("epp_jobs", {
        "amended_dt": None,
        "failures": 1000
    }, {"epp_job_id": epp_job["epp_job_id"]})


def job_failed(epp_job):
    sql.sql_update_one(
        "epp_jobs", {
            "amended_dt": None,
            "failures": epp_job["failures"] + 1,
            "execute_dt": sql.now(60)
        }, {"epp_job_id": epp_job["epp_job_id"]})


EEP_JOB_FUNC = {"dom/update": update_domain_from_db}


def run_epp_item(epp_job):
    if (not sql.has_data(epp_job, "job_type")
            or epp_job["job_type"] not in EEP_JOB_FUNC):
        log(f"ABORT: Missing or invalid job_type for {epp_job['epp_job_id']}",
            gzz(czz()))
        return job_abort(epp_job)

    log(
        f"Executing epp_job {epp_job['epp_job_id']} type " +
        "'{epp_job['job_type']}' retries {epp_job['failures']}", gzz(czz()))
    job_run = EEP_JOB_FUNC[epp_job["job_type"]](epp_job)

    if job_run is None:
        return job_abort(epp_job)
    if job_run:
        return job_worked(epp_job)
    return job_failed(epp_job)


def main():
    global clients

    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-l", '--live', action="store_true")
    parser.add_argument("-c", '--create', help="Create a new domain")
    parser.add_argument("-i", '--info', help="Info a domain")
    parser.add_argument("-u",
                        '--update-domain',
                        help="Update a domain based on its database data",
                        type=int)
    args = parser.parse_args()

    log_init(policy.policy("facility_eppsvr", 170),
             debug=not args.live,
             with_logging=True)

    clients = {p: httpx.Client() for p in tld_lib.ports}
    sql.connect("epprun")

    if args.update_domain is not None:
        return update_domain_from_db(args.update_domain)

    if args.create is not None:
        print(
            ">>> CREATE",
            domain_create(args.create,
                          policy.policy("default_dns_servers", DEFAULT_NS), 1))
        return

    if args.info is not None:
        return test_domain_info(args.info)

    start_up_check()

    log("EEP-SVR RUNNING", gzz(czz()))
    while True:
        query = (f"select * from epp_jobs where execute_dt <= now()" +
                 " and failures < {max_retries} limit 1")
        ret, data = sql.run_select(query)
        if ret and len(data) > 0:
            run_epp_item(data[0])
        else:
            time.sleep(5)


if __name__ == "__main__":
    main()
    if sql.cnx is not None:
        sql.cnx.close()
