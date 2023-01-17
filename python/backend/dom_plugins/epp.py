#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" bacnend call backs to run requests to an EPP registry """

import sys
import json
import base64
import requests

from librar import mysql as sql
from librar import registry
from librar.log import log, init as log_init
from librar.policy import this_policy as policy
from librar import validate
from librar import parse_dom_resp
from librar import parsexml
from librar import static_data
from mailer import spool_email
from backend import whois_priv
from backend import dom_req_xml
from backend import xmlapi
from backend import shared

from backend import dom_handler

DEFAULT_NS = ["ns1.example.com", "ns2.exmaple.com"]


def run_epp_request(this_reg, post_json):
    """ run EPP request to EPP service {this_reg} using {post_json} """
    try:
        client = registry.tld_lib.clients[this_reg["name"]]
        resp = client.post(this_reg["url"], json=post_json, headers=static_data.HEADER)
        if resp.status_code < 200 or resp.status_code > 299:
            log(f"ERROR: {resp.status_code} {this_reg['url']} {resp.content}")
            return None
        ret = json.loads(resp.content)
        return ret
    except (requests.exceptions.RequestException, ValueError) as exc:
        log(f"ERROR: XML Request registry '{this_reg['name']}': {exc}")
        return None
    return None


def start_up_check():
    """ checks that need to be run before this service can be used """
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



def ds_in_list(ds_data, ds_list):
    """ True if DS record {ds_data} is in the list {ds_list} """
    for ds_item in ds_list:
        if (ds_item["keyTag"] == ds_data["keyTag"] and ds_item["alg"] == ds_data["alg"]
                and ds_item["digestType"] == ds_data["digestType"] and ds_item["digest"] == ds_data["digest"]):
            return True
    return False


def domain_renew(bke_job, dom_db):
    """ Renew a domain at an EPP registry """
    name = dom_db["name"]
    job_id = bke_job["backend_id"]

    if not shared.check_have_data(job_id, dom_db, ["expiry_dt"]):
        return False
    if not shared.check_have_data(job_id, bke_job, ["num_years"]):
        return False

    if (years := shared.check_num_years(bke_job)) is None:
        return None

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    xml = run_epp_request(this_reg, dom_req_xml.domain_renew(name, years, dom_db["expiry_dt"].split()[0]))

    if not xml_check_code(job_id, "renew", xml):
        return False

    xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "ren")
    sql.sql_update_one("domains", {"expiry_dt": xml_dom["expiry_dt"]}, {"domain_id": dom_db["domain_id"]})

    return True


def transfer_failed(domain_id):
    """ change domain status to show a transfer failed """
    sql.sql_update_one("domains", {"status_id": static_data.STATUS_TRANS_FAIL}, {"domain_id": domain_id})
    return False


def domain_request_transfer(bke_job, dom_db):
    name = dom_db["name"]
    job_id = bke_job["backend_id"]

    if not shared.check_have_data(job_id, bke_job, ["num_years", "authcode"]):
        return transfer_failed(dom_db["domain_id"])

    if (years := shared.check_num_years(bke_job)) is None:
        transfer_failed(dom_db["domain_id"])
        return None

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    xml = run_epp_request(
        this_reg,
        dom_req_xml.domain_request_transfer(name,
                                            base64.b64decode(bke_job["authcode"]).decode("utf-8"), years))

    if not xml_check_code(job_id, "transfer", xml):
        if (bke_job["failures"] + 1) >= policy.policy("epp_retry_attempts"):
            return transfer_failed(dom_db["domain_id"])
        return False

    update_cols = {}
    if xmlapi.xmlcode(xml) == 1000:
        xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "trn")
        update_cols["expiry_dt"] = xml_dom["expiry_dt"]
        update_cols["status_id"] = static_data.STATUS_LIVE
        sql.sql_update_one("domains", update_cols, {"domain_id": dom_db["domain_id"]})
        spool_email.spool("domain_transferred", [["domains", {
            "domain_id": dom_db["domain_id"]
        }], ["users", {
            "user_id": dom_db["user_id"]
        }]])

    return True


def domain_create(bke_job, dom_db):
    name = dom_db["name"]
    job_id = bke_job["backend_id"]

    ns_list, ds_list = shared.get_domain_lists(dom_db)
    if not shared.check_dom_data(job_id, name, ns_list, ds_list):
        log(f"EPP-{job_id} Domain data failed validation")
        return None

    if (years := shared.check_num_years(bke_job)) is None:
        return None

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    if len(ns_list) > 0:
        run_host_create(this_reg, ns_list)

    xml = run_epp_request(this_reg, dom_req_xml.domain_create(name, ns_list, ds_list, years))
    if not xml_check_code(job_id, "create", xml):
        return False

    xml_dom = parse_dom_resp.parse_domain_info_xml(xml, "cre")

    sql.sql_update_one("domains", {
        "status_id": static_data.STATUS_LIVE,
        "reg_create_dt": xml_dom["created_dt"],
        "expiry_dt": xml_dom["expiry_dt"]
    }, {"domain_id": dom_db["domain_id"]})

    return True


# pylint: disable=unused-argument
def domain_info(bke_job, dom_db):
    this_reg = registry.tld_lib.reg_record_for_domain(dom_db["name"])
    ret = run_epp_request(this_reg, dom_req_xml.domain_info(dom_db["name"]))

    if xmlapi.xmlcode(ret) == 1000:
        return parse_dom_resp.parse_domain_info_xml(ret, "inf")
    return False
# pylint: enable=unused-argument


def epp_get_domain_info(job_id, domain_name):
    this_reg = registry.tld_lib.reg_record_for_domain(domain_name)
    if this_reg is None or "url" not in this_reg:
        log(f"EPP-{job_id} '{domain_name}' this_reg or url not given")
        return None

    xml = run_epp_request(this_reg, dom_req_xml.domain_info(domain_name))

    if not xml_check_code(job_id, "info", xml):
        return None

    return parse_dom_resp.parse_domain_info_xml(xml, "inf")


def set_authcode(bke_job, dom_db):
    job_id = bke_job["backend_id"]
    name = dom_db["name"]

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    if this_reg is None or "url" not in this_reg:
        log(f"Odd: this_reg or url returned None for '{name}")
        return None

    req = dom_req_xml.domain_set_authcode(
        name,
        base64.b64decode(bke_job["authcode"]).decode("utf-8"),
    )

    return xml_check_code(job_id, "info", run_epp_request(this_reg, req))


def domain_update_flags(bke_job, dom_db):
    job_id = bke_job["backend_id"]
    name = dom_db["name"]
    if (epp_info := epp_get_domain_info(job_id, name)) is None:
        return False

    client_locks = {}
    if sql.has_data(dom_db, "client_locks"):
        client_locks = ["client" + lock for lock in dom_db["client_locks"].split(",")]

    add_flags = [item for item in client_locks if item not in epp_info["status"] and item != "ok"]
    del_flags = [item for item in epp_info["status"] if item not in client_locks and item != "ok"]

    if len(add_flags) == 0 and len(del_flags) == 0:
        return True

    this_reg = registry.tld_lib.reg_record_for_domain(name)
    update_xml = dom_req_xml.domain_update_flags(name, add_flags, del_flags)

    return xml_check_code(job_id, "update", run_epp_request(this_reg, update_xml))


def domain_update_from_db(bke_job, dom_db):
    job_id = bke_job["backend_id"]
    name = dom_db["name"]
    if (epp_info := epp_get_domain_info(job_id, name)) is None:
        return False

    return do_domain_update(job_id, name, dom_db, epp_info)


def run_host_create(this_reg, host_list):
    for host in host_list:
        run_epp_request(this_reg, dom_req_xml.host_add(host))


def do_domain_update(job_id, name, dom_db, epp_info):
    this_reg = registry.tld_lib.reg_record_for_domain(name)
    if this_reg is None or "url" not in this_reg:
        return None

    ns_list, ds_list = shared.get_domain_lists(dom_db)
    if not shared.check_dom_data(job_id, name, ns_list, ds_list):
        return None

    add_ns = [item for item in ns_list if item not in epp_info["ns"]]
    del_ns = [item for item in epp_info["ns"] if item not in ns_list]

    add_ds = [ds_data for ds_data in ds_list if not ds_in_list(ds_data, epp_info["ds"])]
    del_ds = [ds_data for ds_data in epp_info["ds"] if not ds_in_list(ds_data, ds_list)]

    if (len(add_ns + del_ns + add_ds + del_ds)) <= 0:
        return True

    if len(add_ns) > 0:
        run_host_create(this_reg, add_ns)

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


# pylint: disable=unused-argument
def domain_expired(bke_job, dom_db):
    # Probably nothing to do for EPP
    return True


def domain_delete(bke_job, dom_db):
    # Probably nothing to do for EPP
    return True
# pylint: enable=unused-argument


def my_hello(__):
    return "EPP: Hello"


def http_price_domains(domlist, years, qry_type):

    if domlist.registry is None or "url" not in domlist.registry:
        return 400, "Unsupported TLD"

    xml = xml_check_with_fees(domlist, years, qry_type)
    resp = domlist.client.post(domlist.registry["url"], json=xml, headers=static_data.HEADER)

    if resp.status_code < 200 or resp.status_code > 299:
        return 400, "Invalid HTTP Response from parent"

    try:
        ret_js = json.loads(resp.content)
        return 200, ret_js
    except ValueError as err:
        log(f"{resp.status_code} === {resp.content.decode('utf8')}")
        log(f"**** JSON FAILED TO PARSE ***** {err}")
        return 400, "Returned JSON Parse Error"

    return 400, "Unexpected Error"


def epp_domain_prices(domlist, num_years=1, qry_type=None):
    if qry_type is None:
        qry_type = ["create", "renew"]
    ok, out_js = http_price_domains(domlist, num_years, qry_type)
    if ok != 200:
        return False, out_js

    xml_p = parsexml.XmlParser(out_js)
    code, ret_js = xml_p.parse_check_message()

    if not code == 1000:
        return False, ret_js

    return True, ret_js


def xml_check_with_fees(domlist, years, qry_type):
    fees_extra = [fees_one(name, years) for name in qry_type]
    return {
        "check": {
            "domain:check": {
                "@xmlns:domain": domlist.xmlns["domain"],
                "domain:name": list(domlist.domobjs)
            }
        },
        "extension": {
            "fee:check": {
                "@xmlns:fee": domlist.xmlns["fee"],
                "fee:currency": domlist.currency["iso"],
                "fee:command": fees_extra
            }
        }
    }


def fees_one(action, years):
    return {
        "@name": action,
        "fee:period": {
            "@unit": "y",
            "#text": str(years),
        }
    }


dom_handler.add_plugin(
    "epp", {
        "hello": my_hello,
        "start_up": start_up_check,
        "dom/update": domain_update_from_db,
        "dom/create": domain_create,
        "dom/renew": domain_renew,
        "dom/transfer": domain_request_transfer,
        "dom/authcode": set_authcode,
        "dom/info": domain_info,
        "dom/delete": domain_delete,
        "dom/recover": domain_renew,
        "dom/expired": domain_expired,
        "dom/flags": domain_update_flags,
        "dom/price": epp_domain_prices
    })

if __name__ == "__main__":
    log_init(with_debug=True)
    if not sql.connect("engine"):
        print("ABORT")
        sys.exit(1)
    registry.start_up()
    start_up_check()
    # print(json.dumps(domain_info(None, {"name": "pant.to.glass"}), indent=3))
    print(domain_update_flags({"backend_id": 999}, {"name": "pant.to.glass", "client_locks": None}))
