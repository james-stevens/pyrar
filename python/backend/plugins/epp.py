#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import base64
import httpx

from librar import mysql as sql
from librar import registry
from librar.log import log
from librar.policy import this_policy as policy
from librar import misc
from librar import validate
from librar import parse_dom_resp
import whois_priv
import dom_req_xml
import xmlapi
import shared

from backend import handler

DEFAULT_NS = ["ns1.example.com", "ns2.exmaple.com"]


def run_epp_request(this_reg, post_json):
    try:
        client = registry.tld_lib.clients[this_reg["name"]]
        resp = client.post(this_reg["url"], json=post_json, headers=misc.HEADER)
        if resp.status_code < 200 or resp.status_code > 299:
            log(f"ERROR: {resp.status_code} {this_reg['url']} {resp.content}")
            return None
        ret = json.loads(resp.content)
        return ret
    except Exception as exc:
        log(f"ERROR: XML Request registry '{this_reg['name']}': {exc}")
        return None
    return None


def start_up_check():
    for name, reg in registry.tld_lib.registry.items():
        if reg["type"] != "epp":
            continue

        if run_epp_request(reg, {"hello": None}) is None:
            log(f"ERROR: EPP Gateway for '{name}' is not working")
            sys.exit(0)

        client = registry.tld_lib.clients[name]
        if not whois_priv.check_privacy_exists(client, reg["url"]):
            msg = (f"ERROR: Registry '{name}' " + "privacy record failed to create")
            log(msg)
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


def domain_renew(epp_job, dom_db):
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    if not shared.check_have_data(job_id, dom_db, ["expiry_dt"]):
        return False
    if not shared.check_have_data(job_id, epp_job, ["num_years"]):
        return False

    if (years := shared.check_num_years(epp_job)) is None:
        return None

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    xml = run_epp_request(this_reg, dom_req_xml.domain_renew(name, years, dom_db["expiry_dt"].split()[0]))

    if not xml_check_code(job_id, "renew", xml):
        return False

    xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "ren")
    sql.sql_update_one("domains", {"expiry_dt": xml_dom["expiry_dt"]}, {"domain_id": dom_db["domain_id"]})

    return True


def transfer_failed(domain_id):
    sql.sql_update_one("domains", {"status_id": misc.STATUE_TRANS_FAIL}, {"domain_id": domain_id})
    return False


def domain_request_transfer(epp_job, dom_db):
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    if not shared.check_have_data(job_id, epp_job, ["num_years", "authcode"]):
        return transfer_failed(dom_db["domain_id"])

    if (years := shared.check_num_years(epp_job)) is None:
        transfer_failed(dom_db["domain_id"])
        return None

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    xml = run_epp_request(
        this_reg,
        dom_req_xml.domain_request_transfer(name,
                                            base64.b64decode(epp_job["authcode"]).decode("utf-8"), years))

    if not xml_check_code(job_id, "transfer", xml):
        if (epp_job["failures"] + 1) >= policy.policy("epp_retry_attempts"):
            return transfer_failed(dom_db["domain_id"])
        return False

    update_cols = {}
    if xml_code == 1000:
        xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "trn")
        update_cols["expiry_dt"] = xml_dom["expiry_dt"]
        update_cols["status_id"] = misc.STATUS_LIVE
        sql.sql_update_one("domains", update_cols, {"domain_id": dom_db["domain_id"]})

    return True


def domain_create(epp_job, dom_db):
    name = dom_db["name"]
    job_id = epp_job["epp_job_id"]

    ns_list, ds_list = shared.get_domain_lists(dom_db)
    if not check_dom_data(job_id, name, ns_list, ds_list):
        log(f"EPP-{job_id} Domain data failed validation")
        return None

    if (years := shared.check_num_years(epp_job)) is None:
        return None

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    if len(ns_list) > 0:
        run_host_create(job_id, this_reg, ns_list)

    xml = run_epp_request(this_reg, dom_req_xml.domain_create(name, ns_list, ds_list, years))
    if not xml_check_code(job_id, "create", xml):
        return False

    xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "cre")

    sql.sql_update_one("domains", {
        "status_id": misc.STATUS_LIVE,
        "reg_create_dt": xml_dom["created_dt"],
        "expiry_dt": xml_dom["expiry_dt"]
    }, {"domain_id": dom_db["domain_id"]})

    return True


def domain_info(epp_job, dom_db):

    this_reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    ret = run_epp_request(this_reg, dom_req_xml.domain_info(dom_db["name"]))

    if xmlapi.xmlcode(ret) == 1000:
        return parse_dom_resp.parse_domain_info_xml(ret, "inf")
    return False


def epp_get_domain_info(job_id, domain_name):
    this_reg = registry.tld_lib.reg_record_for_domain(domain_name)
    if this_reg is None or "url" not in this_reg:
        log(f"EPP-{job_id} '{domain_name}' this_reg or url not given")
        return None

    xml = run_epp_request(this_reg, dom_req_xml.domain_info(domain_name))

    if not xml_check_code(job_id, "info", xml):
        return None

    return parse_dom_resp.parse_domain_info_xml(xml, "inf")


def set_authcode(epp_job, dom_db):
    job_id = epp_job["epp_job_id"]
    name = dom_db["name"]

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    if this_reg is None or "url" not in this_reg:
        log(f"Odd: this_reg or url returned None for '{name}")
        return None

    req = dom_req_xml.domain_set_authcode(
        name,
        base64.b64decode(epp_job["authcode"]).decode("utf-8"),
    )

    return xml_check_code(job_id, "info", run_epp_request(this_reg, req))


def domain_update_from_db(epp_job, dom_db):
    job_id = epp_job["epp_job_id"]
    name = dom_db["name"]
    if (epp_info := epp_get_domain_info(job_id, name)) is None:
        return False

    return do_domain_update(job_id, name, dom_db, epp_info)


def run_host_create(job_id, this_reg, host_list):
    for host in host_list:
        run_epp_request(this_reg, dom_req_xml.host_add(host))


def do_domain_update(job_id, name, dom_db, epp_info):
    this_reg = registry.tld_lib.reg_record_for_domain(name)
    if this_reg is None or "url" not in this_reg:
        return None

    ns_list, ds_list = shared.get_domain_lists(dom_db)
    if not check_dom_data(job_id, name, ns_list, ds_list):
        return None

    add_ns = [item for item in ns_list if item not in epp_info["ns"]]
    del_ns = [item for item in epp_info["ns"] if item not in ns_list]

    add_ds = [ds_data for ds_data in ds_list if not ds_in_list(ds_data, epp_info["ds"])]
    del_ds = [ds_data for ds_data in epp_info["ds"] if not ds_in_list(ds_data, ds_list)]

    if (len(add_ns + del_ns + add_ds + del_ds)) <= 0:
        return True

    if len(add_ns) > 0:
        run_host_create(job_id, this_reg, add_ns)

    if not sql.has_data(dom_db, "reg_create_dt") or dom_db["reg_create_dt"] != epp_info["created_dt"]:
        sql.sql_update_one("domains", {"reg_create_dt": epp_info["created_dt"]}, {"domain_id": dom_db["domain_id"]})

    update_xml = dom_req_xml.domain_update(name, add_ns, del_ns, add_ds, del_ds)

    return xml_check_code(job_id, "update", run_epp_request(this_reg, update_xml))


def xml_check_code(job_id, desc, xml):
    xml_code = xmlapi.xmlcode(xml)
    if xml_code > 1050:
        log(f"EPP-{job_id} XML {desc} request gave {xml_code}")
        if xml_code != 9999:
            log(f"EPP-{job_id} {json.dumps(xml)}")
        return False

    return True


def my_hello(__):
    return "EPP: Hello"


handler.add_plugin(
    "epp", {
        "hello": my_hello,
        "start_up": start_up_check,
        "dom/update": domain_update_from_db,
        "dom/create": domain_create,
        "dom/renew": domain_renew,
        "dom/transfer": domain_request_transfer,
        "dom/authcode": set_authcode,
        "dom/info": domain_info
    })
