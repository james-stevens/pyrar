#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import httpx
import argparse

from inspect import currentframe as czz, getframeinfo as gzz

from lib.providers import tld_lib
from lib.log import log, init as log_init
from lib.policy import this_policy as policy
from lib import api
from lib import validate
import whois_priv
import domxml
import xmlapi

clients = None
retries = policy.policy("epp_retry_attempts", 3)

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
        ret = request_json(prov, {"hello": None})
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


def make_add_del_lists(truth, desire):
    """ make lists of NS to add/remove """
    return [item for item in desire if item not in truth
            ], [item for item in truth if item not in desire]


def check_dom_data(domain, data_list, validate_func):
    if (ret := validate.check_domain_name(domain)) is not None:
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


def update_domain_ns(domain, ns_list):
    """ update name server of {domain} to {ns_list} """
    if not check_dom_data(domain, ns_list, validate.is_valid_fqdn):
        return None

    prov, url = tld_lib.http_req(domain)
    ret = request_json(prov, domxml.domain_info(domain), url)

    dom_data = domxml.parse_domain_info(ret)
    if "ns" not in dom_data:
        return False

    add_ns, del_ns = make_add_del_lists(dom_data["ns"], ns_list)

    if len(add_ns) == 0 and len(del_ns) == 0:
        return True

    print(">>>>> ADD_NS", add_ns)
    print(">>>>> DEL_NS", del_ns)
    update_xml = domxml.domain_update_ns(domain, add_ns, del_ns)
    ret = request_json(prov, update_xml, url)
    return xmlapi.xmlcode(ret) == 1000


def ds_in_list(ds_data, ds_list):
    for ds_item in ds_list:
        if (ds_item["keyTag"] == ds_data["keyTag"]
                and ds_item["alg"] == ds_data["alg"]
                and ds_item["digestType"] == ds_data["digestType"]
                and ds_item["digest"] == ds_data["digest"]):
            return True
    return False


def make_add_del_ds(truth, desire):
    return [ds_data for ds_data in desire if not ds_in_list(ds_data, truth)], [
        ds_data for ds_data in truth if not ds_in_list(ds_data, desire)
    ]


def update_domain_ds(domain, ds_list):
    """ update ds records of {domain} to {ds_list} """
    if not check_dom_data(domain, ds_list, validate.is_valid_ds):
        return None

    prov, url = tld_lib.http_req(domain)
    ret = request_json(prov, domxml.domain_info(domain), url)

    dom_data = domxml.parse_domain_info(ret)
    if "ds" not in dom_data:
        return False

    add_ds, del_ds = make_add_del_ds(dom_data["ds"], ds_list)

    if len(add_ds) == 0 and len(del_ds) == 0:
        return True

    print(">>>>> ADD_DS", add_ds)
    print(">>>>> DEL_DS", del_ds)

    update_xml = domxml.domain_update_ds(domain, add_ds, del_ds)
    ret = request_json(prov, update_xml, url)
    print(json.dumps(update_xml,indent=2))
    print(json.dumps(ret,indent=2))
    return xmlapi.xmlcode(ret) == 1000


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


def main():
    global clients

    parser = argparse.ArgumentParser(description='EPP Jobs Runner')
    parser.add_argument("-l", '--live', action="store_true")
    parser.add_argument("-c", '--create', help="Create a new domain")
    parser.add_argument("-i", '--info', help="Info a domain")
    parser.add_argument("-n", '--ns-list', help="list of name servers")
    parser.add_argument("-d", '--ds-list', help="list of DS records")
    args = parser.parse_args()
    debug = not args.live

    log_init(policy.policy("facility_eppsvr", 170),
             debug=debug,
             with_logging=True)

    clients = {p: httpx.Client() for p in tld_lib.ports}

    if args.create is not None:
        print(
            ">>> CREATE",
            domain_create(args.create,
                          policy.policy("default_dns_servers", DEFAULT_NS), 1))
        return

    if args.info is not None:
        if args.ns_list is not None:
            print(">>>> Update NS",
                  update_domain_ns(args.info, args.ns_list.split(",")))
            return
        elif args.ds_list is not None:
            print(
                ">>>> Update DS",
                update_domain_ds(
                    args.info,
                    [validate.frag_ds(ds) for ds in args.ds_list.split(",")]))
            return
        else:
            return test_domain_info(args.info)

    start_up_check()

    print("RUNNING")


if __name__ == "__main__":
    main()
