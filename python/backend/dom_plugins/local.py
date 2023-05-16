#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" bacnend call-backs for running as registry locally """

from librar.log import log, init as log_init

from librar.mysql import sql_server as sql
from librar import registry, pdns, static, passwd, misc
from librar.policy import this_policy as policy

from backend import shared
from backend import dom_handler


def tld_pdns_check(name):
    """ check if domain exists in pdns """
    if (tld := registry.tld_lib.tld_of_name(name)) is None:
        return None
    pdns.create_zone(tld, True, ensure_zone=True, client_zone=False)
    return tld


def domain_delete(bke_job, dom):
    """ run dom/delete request """
    return remove_parent_records(None, bke_job, dom.dom_db)


def remove_parent_records(bke_job, dom):
    """ remove the SLD from the TLD zone (in pdns) """
    job_id = bke_job["backend_id"]
    name = dom.dom_db["name"]

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


def domain_expired(bke_job, dom):
    """ run dom/expired request for type=local"""
    return remove_parent_records(bke_job, dom)


def domain_create(bke_job, dom):
    """ run dom/create request for type=local """
    if (years := shared.check_num_years(bke_job)) is None:
        return False

    log(f"domain_create: {dom.dom_db['name']}, {dom.dom_db['expiry_dt']} yrs={years}")

    if (ok_add := add_years_to_expiry(years, dom.dom_db, "created_dt")):
        create_update_request(bke_job)

    return ok_add


def create_update_request(bke_job):
    """ create a dom/update request to sync dom's data in TLD zone """
    new_bke = {
        "domain_id": bke_job["domain_id"],
        "user_id": bke_job["user_id"],
        "execute_dt": misc.now(),
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
        if "reg_data" in zone_rec and zone_rec["reg_data"]["type"] == "local":
            pdns.create_zone(zone, True, ensure_zone=True, client_zone=False, auto_catalog=True)

    return True


def needs_parent_records(dom_db):
	return (misc.has_data(dom_db,"ns") and dom_db["ns"] != policy.policy("dns_servers")) or pdns.zone_exists(dom_db["name"])


def domain_update_from_db(bke_job, dom):
    """ run dom/update request to sync NS & DS into TLD zone """
    job_id = bke_job["backend_id"]
    name = dom.dom_db["name"]

    if (tld := tld_pdns_check(name)) is None:
        log(f"EPP-{job_id}: tld_pdns_check failed for '{name}'")
        return False

    rrs = {"name": name, "type": "NS", "data": []}
    if needs_parent_records(dom.dom_db):
        rrs["data"] = [d.strip(".") + "." for d in dom.dom_db["ns"].split(",")]

    ok_ns, __ = pdns.update_rrs(tld, rrs)

    rrs = {"name": name, "type": "DS", "data": []}
    if needs_parent_records(dom.dom_db) and misc.has_data(dom.dom_db, "ds"):
        rrs["data"] = dom.dom_db["ds"].split(",")

    ok_ds, __ = pdns.update_rrs(tld, rrs)

    return ok_ns and ok_ds


def domain_request_transfer(bke_job, dom):
    """ run dom/transfer request """
    if not misc.has_data(bke_job, "authcode") or not misc.has_data(dom.dom_db, "authcode"):
        return None

    if dom.dom_db["user_id"] == bke_job["user_id"]:
        return True

    if not passwd.compare(dom.dom_db["authcode"], bke_job["authcode"]):
        return None

    return sql.sql_update_one("domains", {
        "authcode": None,
        "user_id": bke_job["user_id"]
    }, {"domain_id": dom.dom_db["domain_id"]})


def add_years_to_expiry(years, dom_db, start_date="expiry_dt"):
    """ Set dom_db.expiry_dt = {years} + dom_db.{start_date} and update status """
    log(f"Adding {years} yrs to '{dom_db['name']}'/{start_date}")
    values = [
        f"expiry_dt = date_add({start_date},interval {years} year)",
        f"status_id = if (expiry_dt > now(),{static.STATUS_LIVE},{static.STATUS_EXPIRED})", "amended_dt = now()"
    ]
    return sql.sql_update_one("domains", ",".join(values), {"domain_id": dom_db["domain_id"]})


def domain_renew(bke_job, dom):
    """ run dom/renew request """
    if (years := shared.check_num_years(bke_job)) is None:
        return False
    return add_years_to_expiry(years, dom.dom_db)


def domain_recover(bke_job, dom):
    """ run dom/recover request """
    if (years := shared.check_num_years(bke_job)) is None:
        return False
    if (ok_add := add_years_to_expiry(years, dom.dom_db)):
        create_update_request(bke_job)
    return ok_add


def my_hello(__):
    """ test fn """
    return "LOCAL: Hello"


def domain_info(bke_job, dom):
    """ noting to do for type=local """
    return dom.dom_db


def set_authcode(bke_job, dom):
    """ nothing to do, set by webui/domains code """
    return True


def domain_update_flags(bke_job, dom):
    """ nothing to do for `local` """
    return True


def get_class_from_name(name):
    """ support for domain:class, premium pricing. Return class for {name} """
    ok, class_db = sql.sql_select_one("class_by_name", {"name": name}, "class")
    if ok and class_db and len(class_db) > 0:
        return class_db["class"].lower()

    if (idx := name.find(".")) < 0:
        return "standard"

    where = f"(unhex('{misc.ashex(name[:idx])}') regexp name_regexp) and zone = unhex('{misc.ashex(name[idx+1:])}')"
    ok, class_db = sql.sql_select_one("class_by_regexp", where, "class")
    if ok and class_db and len(class_db) > 0:
        return class_db["class"].lower()

    return "standard"


def local_domain_prices(domlist, num_years=1, qry_type=None):
    """ set up blank prices to be filled in by registry.tld_lib.multiply_values """
    if qry_type is None:
        qry_type = ["create", "renew"]
    ret_doms = []
    for dom in domlist.domobjs:
        add_dom = {"name": dom, "num_years": num_years, "avail": True, "class": get_class_from_name(dom)}
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
