#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import base64

from librar.log import log, debug, init as log_init

from librar import mysql as sql
from librar import registry
from librar import pdns
from librar import misc
from librar import passwd

from backend import handler
from backend import shared


def tld_pdns_check(name):
    if (tld := registry.tld_lib.tld_of_name(name)) is None:
        return None

    if tld not in pdns.all_pdns_zones:
        pdns.create_zone(tld, True)

    return tld


def domain_delete(bke_job, dom_db):
    job_id = bke_job["backend_id"]
    name = dom_db["name"]

    if (tld := tld_pdns_check(name)) is None:
        log(f"EPP-{job_id}: tld_pdns_check failed for '{name}'")
        return False

    # remove SLD from TLD in pdns - A & AAAA incase they used the SLD as an NS name
    ok_a = pdns.update_rrs(tld, {"name": name, "type": "A", "data": []})
    ok_aaaa = pdns.update_rrs(tld, {"name": name, "type": "AAAA", "data": []})
    ok_ns = pdns.update_rrs(tld, {"name": name, "type": "NS", "data": []})
    ok_ds = pdns.update_rrs(tld, {"name": name, "type": "DS", "data": []})

    # need code to remove glue records, when supported

    return ok_ns and ok_ds and ok_a and ok_aaaa


def domain_expired(bke_job, dom_db):
    return domain_delete(bke_job, dom_db)


def domain_create(bke_job, dom_db):
    ok_add = add_yrs(bke_job, dom_db)
    ok_updt = domain_update_from_db(bke_job, dom_db)
    return ok_add and ok_updt


def start_up_check():
    pdns.start_up()
    check_tlds_exist()


def check_tlds_exist():
    for zone, zone_rec in registry.tld_lib.zone_data.items():
        if ("reg_data" in zone_rec and zone_rec["reg_data"]["type"] == "local" and zone not in pdns.all_pdns_zones):
            pdns.create_zone(zone, True)

    return True


def domain_update_from_db(bke_job, dom_db):
    job_id = bke_job["backend_id"]
    name = dom_db["name"]

    if (tld := tld_pdns_check(name)) is None:
        log(f"EPP-{job_id}: tld_pdns_check failed for '{name}'")
        return False

    rrs = {"name": name, "type": "NS", "data": []}
    if sql.has_data(dom_db, "ns"):
        rrs["data"] = [d.strip(".") + "." for d in dom_db["ns"].split(",")]

    ok_ns = pdns.update_rrs(tld, rrs)

    rrs = {"name": name, "type": "DS", "data": []}
    if sql.has_data(dom_db, "ds"):
        rrs["data"] = dom_db["ds"].split(",")

    ok_ds = pdns.update_rrs(tld, rrs)

    return ok_ns and ok_ds


def domain_request_transfer(bke_job, dom_db):
    if not sql.has_data(bke_job, "authcode") or not sql.has_data(dom_db, "authcode"):
        debug(f"Missing field")
        return None

    if dom_db["user_id"] == bke_job["user_id"]:
        return True

    if not passwd.compare(dom_db["authcode"], bke_job["authcode"]):
        debug(f"passwords do not match {dom_db['authcode']} {enc_pass}")
        return None

    return sql.sql_update_one("domains", {
        "authcode": None,
        "user_id": bke_job["user_id"]
    }, {"domain_id": dom_db["domain_id"]})



def add_yrs(bke_job, dom_db):
    values = [
        f"expiry_dt = date_add(expiry_dt,interval {bke_job['num_years']} year)",
        f"status_id = if (expiry_dt > now(),{misc.STATUS_LIVE},{misc.STATUS_EXPIRED})",
        "amended_dt = now()"
        ]
    return sql.sql_update_one("domains",",".join(values),{"domain_id": dom_db["domain_id"]})


def domain_renew(bke_job, dom_db):
    return add_yrs(bke_job, dom_db)


def domain_recover(bke_job, dom_db):
    ok_add = add_yrs(bke_job, dom_db)
    ok_updt = domain_update_from_db(bke_job, dom_db)
    return ok_add and ok_updt


def domain_info(bke_job, dom_db):
    return dom_db


def set_authcode(bke_job, dom_db):
    password = passwd.crypt(base64.b64decode(bke_job["authcode"])) if sql.has_data(bke_job, "authcode") else None
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
        "dom/authcode": set_authcode,
        "dom/delete": domain_delete,
        "dom/expired": domain_expired,
        "dom/info": domain_info,
        "dom/recover": domain_recover
    })

if __name__ == "__main__":
    log_init(with_debug=True)
    start_up_check()
