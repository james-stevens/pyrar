#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" bacnend call-backs for running as registry locally """

import base64

from librar.log import log, init as log_init

from librar import mysql as sql
from librar import registry
from librar import pdns
from librar import static_data
from librar import passwd

from backend import shared
from backend import dom_handler


def tld_pdns_check(name):
    """ check if domain exists in pdns """
    if (tld := registry.tld_lib.tld_of_name(name)) is None:
        return None

    if not pdns.zone_exists(tld):
        pdns.create_zone(tld, True)

    return tld


def domain_delete(bke_job, dom_db):
    """ run dom/delete request """
    return remove_parent_records(bke_job, dom_db)


def remove_parent_records(bke_job, dom_db):
    """ remove the SLD from the TLD zone (in pdns) """
    job_id = bke_job["backend_id"]
    name = dom_db["name"]

    if (tld := tld_pdns_check(name)) is None:
        log(f"EPP-{job_id}: tld_pdns_check failed for '{name}'")
        return False

    # remove SLD from TLD in pdns - A & AAAA incase they used the SLD as an NS name
    ok_a, __ = pdns.update_rrs(tld, {"name": name, "type": "A", "data": []})
    ok_aaaa, __ = pdns.update_rrs(tld, {"name": name, "type": "AAAA", "data": []})
    ok_ns, __ = pdns.update_rrs(tld, {"name": name, "type": "NS", "data": []})
    ok_ds, __ = pdns.update_rrs(tld, {"name": name, "type": "DS", "data": []})

    # CODE
    # need code to remove glue records, when supported

    return ok_ns and ok_ds and ok_a and ok_aaaa


def domain_expired(bke_job, dom_db):
    """ run dom/expired request for type=local"""
    return remove_parent_records(bke_job, dom_db)


def domain_create(bke_job, dom_db):
    """ run dom/create request for type=local """
    if (years := shared.check_num_years(bke_job)) is None:
        return False

    log(f"domain_create: {dom_db['name']}, {dom_db['expiry_dt']} yrs={years}")

    if (ok_add := add_years_to_expiry(years, dom_db, "created_dt")):
        create_update_request(bke_job)

    return ok_add


def create_update_request(bke_job):
    """ create a dom/update request to sync dom's data in TLD zone """
    new_bke = {
        "domain_id": bke_job["domain_id"],
        "user_id": bke_job["user_id"],
        "execute_dt": sql.now(),
        "created_dt": None,
        "amended_dt": None,
        "job_type": "dom/update",
        "failures": 0
    }
    sql.sql_insert("backend", new_bke)


def start_up_check():
    """ needs to be run before these can be used """
    pdns.start_up()
    check_tlds_exist()


def check_tlds_exist():
    """ check all TLDs of type=local exist in pdns """
    for zone, zone_rec in registry.tld_lib.zone_data.items():
        if ("reg_data" in zone_rec and zone_rec["reg_data"]["type"] == "local" and not pdns.zone_exists(zone)):
            pdns.create_zone(zone, True)

    return True


def domain_update_from_db(bke_job, dom_db):
    """ run dom/update request to sync NS & DS into TLD zone """
    job_id = bke_job["backend_id"]
    name = dom_db["name"]

    if (tld := tld_pdns_check(name)) is None:
        log(f"EPP-{job_id}: tld_pdns_check failed for '{name}'")
        return False

    rrs = {"name": name, "type": "NS", "data": []}
    if sql.has_data(dom_db, "ns"):
        rrs["data"] = [d.strip(".") + "." for d in dom_db["ns"].split(",")]

    ok_ns, __ = pdns.update_rrs(tld, rrs)

    rrs = {"name": name, "type": "DS", "data": []}
    if sql.has_data(dom_db, "ds"):
        rrs["data"] = dom_db["ds"].split(",")

    ok_ds, __ = pdns.update_rrs(tld, rrs)

    return ok_ns and ok_ds


def domain_request_transfer(bke_job, dom_db):
    """ run dom/transfer request """
    if not sql.has_data(bke_job, "authcode") or not sql.has_data(dom_db, "authcode"):
        return None

    if dom_db["user_id"] == bke_job["user_id"]:
        return True

    if not passwd.compare(dom_db["authcode"], bke_job["authcode"]):
        return None

    return sql.sql_update_one("domains", {
        "authcode": None,
        "user_id": bke_job["user_id"]
    }, {"domain_id": dom_db["domain_id"]})


def add_years_to_expiry(years, dom_db, start_date="expiry_dt"):
    """ Set dom_db.expiry_dt = {years} + dom_db.{start_date} and update status """
    log(f"Adding {years} yrs to '{dom_db['name']}'/{start_date}")
    values = [
        f"expiry_dt = date_add({start_date},interval {years} year)",
        f"status_id = if (expiry_dt > now(),{static_data.STATUS_LIVE},{static_data.STATUS_EXPIRED})",
        "amended_dt = now()"
    ]
    return sql.sql_update_one("domains", ",".join(values), {"domain_id": dom_db["domain_id"]})


def domain_renew(bke_job, dom_db):
    """ run dom/renew request """
    if (years := shared.check_num_years(bke_job)) is None:
        return False
    return add_years_to_expiry(years, dom_db)


def domain_recover(bke_job, dom_db):
    """ run dom/recover request """
    if (years := shared.check_num_years(bke_job)) is None:
        return False
    if (ok_add := add_years_to_expiry(years, dom_db)):
        create_update_request(bke_job)
    return ok_add


# pylint: disable=unused-argument
def domain_info(bke_job, dom_db):
    """ noting to do for type=local """
    return dom_db


# pylint: enable=unused-argument


def set_authcode(bke_job, dom_db):
    """ run dom/authcode request """
    password = passwd.crypt(base64.b64decode(bke_job["authcode"])) if sql.has_data(bke_job, "authcode") else None
    return sql.sql_update_one("domains", {"authcode": password}, {"domain_id": dom_db["domain_id"]})


def my_hello(__):
    """ test fn """
    return "LOCAL: Hello"


# pylint: disable=unused-argument
def domain_update_flags(bke_job, dom_db):
    """ nothing to do for `local` """
    return True


# pylint: enable=unused-argument


def local_domain_prices(domlist, num_years=1, qry_type=None):
    """ set up blank prices to be filled in by registry.tld_lib.multiply_values """
    if qry_type is None:
        qry_type = ["create", "renew"]
    ret_doms = []
    for dom in domlist.domobjs:
        add_dom = {"name": dom, "num_years": num_years, "avail": True}
        for qry in qry_type:
            add_dom[qry] = None

        ret_doms.append(add_dom)

    return True, ret_doms


dom_handler.add_plugin(
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
        "dom/rawinfo": domain_info,
        "dom/recover": domain_recover,
        "dom/flags": domain_update_flags,
        "dom/price": local_domain_prices
    })

if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("engine")
    registry.start_up()
    start_up_check()
