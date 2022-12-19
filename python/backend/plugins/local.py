#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import base64

from librar.log import log, debug, init as log_init

from librar import mysql as sql
from librar import registry
from librar import pdns
from librar import passwd

from backend import handler
from backend import shared


def tld_pdns_check(name):
    if (tld := registry.tld_lib.tld_of_name(name)) is None:
        return None

    if tld not in pdns.all_pdns_zones:
        pdns.create_zone(tld, True)

    return tld


def domain_create(epp_job, dom_db):
    values = [
        f"status_id = {misc.STATUS_LIVE}",
        f"expiry_dt = date_add(expiry_dt,interval {epp_job['num_years']} year)",
        "amended_dt = now()"
        ]
    sql.sql_update_one("domains",",".join(values),{"domain_id": dom_db["domain_id"]})
    return domain_update_from_db(epp_job, dom_db)


def start_up_check():
    pdns.start_up()
    for zone, zone_rec in registry.tld_lib.zone_data.items():
        if ("reg_data" in zone_rec and zone_rec["reg_data"]["type"] == "local" and zone not in pdns.all_pdns_zones):
            pdns.create_zone(zone, True)

    return True


def domain_update_from_db(epp_job, dom_db):
    job_id = epp_job["epp_job_id"]
    name = dom_db["name"]

    if (tld := tld_pdns_check(name)) is None:
        log(f"EPP-{job_id}: tld_pdns_check failed for '{name}'")
        return False

    rrs = {"name": name, "type": "NS", "data": []}
    if sql.has_data(dom_db, "name_servers"):
        rrs["data"] = [d + "." for d in dom_db["name_servers"].split(",")]

    ok_ns = pdns.update_rrs(tld, rrs)

    rrs = {"name": name, "type": "DS", "data": []}
    if sql.has_data(dom_db, "ds_recs"):
        rrs["data"] = dom_db["ds_recs"].split(",")

    ok_ds = pdns.update_rrs(tld, rrs)

    return ok_ns and ok_ds


def domain_request_transfer(epp_job, dom_db):
    if not sql.has_data(epp_job, "authcode") or not sql.has_data(dom_db, "authcode"):
        debug(f"Missing field")
        return None

    if dom_db["user_id"] == epp_job["user_id"]:
        return True

    if not passwd.compare(dom_db["authcode"], epp_job["authcode"]):
        debug(f"passwords do not match {dom_db['authcode']} {enc_pass}")
        return None

    return sql.sql_update_one("domains", {
        "authcode": None,
        "user_id": epp_job["user_id"]
    }, {"domain_id": dom_db["domain_id"]})


def domain_renew(epp_job, dom_db):
    return sql.sql_update_one("domains",
                              f"expiry_dt=date_add(expiry_dt,interval {epp_job['num_years']} year),amended_dt=now()",
                              {"domain_id": dom_db["domain_id"]})


def set_authcode(epp_job, dom_db):
    password = passwd.crypt(base64.b64decode(epp_job["authcode"])) if sql.has_data(epp_job, "authcode") else None
    return sql.sql_update_one("domains", {"authcode": password}, {"domain_id": dom_db["domain_id"]})


def my_hello(__):
    return "LOCAL: Hello"


handler.add_plugin(
    "local", {
        "hello": my_hello,
        "start_up": start_up_check,
        "dom/update": domain_update_from_db,
        "dom/create": domain_create,
        "dom/renew": domain_renew,
        "dom/transfer": domain_request_transfer,
        "dom/authcode": set_authcode
    })

if __name__ == "__main__":
    log_init(with_debug=True)
    start_up()
