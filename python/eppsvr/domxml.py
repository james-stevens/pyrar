#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json
import whois_priv


def domain_info(name):
    return {
        "info": {
            "domain:info": {
                "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name": {
                    "@hosts": "all",
                    "#text": name
                }
            }
        }
    }


def domain_create(name, ns_list, years):
    return {
        "create": {
            "domain:create": {
                "@xmlns:domain":
                "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name":
                name,
                "domain:period": {
                    "@unit": "y",
                    "#text": str(years)
                },
                "domain:ns": {
                    "domain:hostObj": ns_list
                },
                "domain:registrant":
                whois_priv.WHOIS_PRIVACY_ID,
                "domain:contact": [{
                    "@type": "admin",
                    "#text": whois_priv.WHOIS_PRIVACY_ID
                }, {
                    "@type": "tech",
                    "#text": whois_priv.WHOIS_PRIVACY_ID
                }, {
                    "@type": "billing",
                    "#text": whois_priv.WHOIS_PRIVACY_ID
                }]
            }
        }
    }


def domain_update(domain, add_ns, del_ns, add_ds, del_ds):

    update_data = {
        "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
        "domain:name": domain
    }

    if len(add_ns) > 0:
        update_data["domain:add"] = {"domain:ns": {"domain:hostObj": add_ns}}

    if len(del_ns) > 0:
        update_data["domain:rem"] = {"domain:ns": {"domain:hostObj": del_ns}}

    full_xml = {"update": {"domain:update": update_data}}

    if len(add_ds) > 0 or len(del_ds) > 0:
        full_xml["extension"] = { "secDNS:update": { "@xmlns:secDNS": "urn:ietf:params:xml:ns:secDNS-1.1" } }
        sec_dns = full_xml["extension"]["secDNS:update"]
        if len(add_ds) > 0:
            sec_dns["secDNS:add"] = { "secDNS:dsData": [pad_ds(ds) for ds in add_ds] }
        if len(del_ds) > 0:
            sec_dns["secDNS:rem"] = { "secDNS:dsData": [pad_ds(ds) for ds in del_ds] }

    return full_xml


def pad_ds(ds_dt):
    return {"secDNS:" + tag: val for tag, val in ds_dt.items()}


def unroll_one_ds(ds_data):
    return {
        tag: ds_data["secDNS:" + tag]
        for tag in ["keyTag", "alg", "digestType", "digest"]
    }


def unroll_one_ns_attr(ns_data):
    return ns_data["domain:hostName"]


def parse_domain_info(xml):
    data = {}
    if "extension" in xml and "secDNS:infData" in xml[
            "extension"] and "secDNS:dsData" in xml["extension"][
                "secDNS:infData"]:
        ds_data = xml["extension"]["secDNS:infData"]["secDNS:dsData"]
        if isinstance(ds_data, dict):
            data["ds"] = [unroll_one_ds(ds_data)]
        elif isinstance(ds_data, list):
            data["ds"] = [unroll_one_ds(item) for item in ds_data]

    dom_data = xml["resData"]["domain:infData"]
    if isinstance(dom_data["domain:status"], dict):
        data["status"] = [dom_data["domain:status"]["@s"]]
    elif isinstance(dom_data["domain:status"], list):
        data["status"] = [
            item["@s"] for item in dom_data["domain:status"] if "@s" in item
        ]

    dom_ns = dom_data["domain:ns"]
    if "domain:hostAttr" in dom_ns:
        if isinstance(dom_ns["domain:hostAttr"], dict):
            data["ns"] = [unroll_one_ns_attr(dom_ns["domain:hostAttr"])]
        elif isinstance(dom_ns["domain:hostAttr"], list):
            data["ns"] = [
                unroll_one_ns_attr(item) for item in dom_ns["domain:hostAttr"]
            ]

    data["create_dt"] = dom_data["domain:crDate"][:10] + " " + dom_data[
        "domain:crDate"][11:19]
    data["expiry_dt"] = dom_data["domain:exDate"][:10] + " " + dom_data[
        "domain:exDate"][11:19]
    data["name"] = dom_data["domain:name"]
    return data


if __name__ == "__main__":
    print(
        json.dumps(
            domain_create("audi.for.sale", ["ns1.dns.com", "ns2.dns.com"], 1)))
