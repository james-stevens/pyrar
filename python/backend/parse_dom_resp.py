#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" parse a json epp dom object into something nicer """


def unroll_one_ds(ds_data):
    return {tag: ds_data["secDNS:" + tag] for tag in ["keyTag", "alg", "digestType", "digest"]}


def unroll_one_ns_attr(ns_data):
    return ns_data["domain:hostName"]


def epp_dt_to_sql(src, which_property):
    if which_property not in src:
        return None
    return src[which_property][:10] + " " + src[which_property][11:19]


def parse_domain_info_xml(xml, data_type):
    data = {"ds": [], "ns": [], "status": []}
    if "extension" in xml and f"secDNS:{data_type}Data" in xml["extension"] and "secDNS:dsData" in xml["extension"][
            f"secDNS:{data_type}Data"]:
        ds_data = xml["extension"][f"secDNS:{data_type}Data"]["secDNS:dsData"]
        if isinstance(ds_data, dict):
            data["ds"] = [unroll_one_ds(ds_data)]
        elif isinstance(ds_data, list):
            data["ds"] = [unroll_one_ds(item) for item in ds_data]
        data["ds"].sort()

    dom_data = xml["resData"][f"domain:{data_type}Data"]
    if "domain:status" in dom_data:
        if isinstance(dom_data["domain:status"], dict):
            data["status"] = [dom_data["domain:status"]["@s"]]
        elif isinstance(dom_data["domain:status"], list):
            data["status"] = [item["@s"] for item in dom_data["domain:status"] if "@s" in item]
        data["status"].sort()

    if "domain:ns" in dom_data:
        dom_ns = dom_data["domain:ns"]
        if "domain:hostAttr" in dom_ns:
            if isinstance(dom_ns["domain:hostAttr"], dict):
                data["ns"] = [unroll_one_ns_attr(dom_ns["domain:hostAttr"])]
            elif isinstance(dom_ns["domain:hostAttr"], list):
                data["ns"] = [unroll_one_ns_attr(item) for item in dom_ns["domain:hostAttr"]]
        data["ns"].sort()

    data["created_dt"] = epp_dt_to_sql(dom_data, "domain:crDate")
    data["expiry_dt"] = epp_dt_to_sql(dom_data, "domain:exDate")
    data["name"] = dom_data["domain:name"]

    if "domain:clID" in dom_data:
        data["registrar"] = dom_data["domain:clID"]

    return data
