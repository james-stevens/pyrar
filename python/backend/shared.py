#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import inspect

from librar.log import log
from librar.policy import this_policy as policy
from librar import mysql as sql
from librar import validate


def event_log(notes, bke_job):
    misc.event_log({
        "event_type": "BackEnd:" + bke_job["job_type"],
        "domain_id": bke_job["domain_id"],
        "user_id": bke_job["user_id"],
        "who_did_it": "backend",
        "from_where": "localhost",
        "notes": notes
    })


def check_have_data(job_id, dom_db, items):
    for item in items:
        if not sql.has_data(dom_db, item):
            log(f"BKE-{job_id} '{item}' missing or blank")
            return False
    return True


def check_num_years(bke_job):
    job_id = bke_job["backend_id"]
    if not check_have_data(job_id, bke_job, ["num_years"]):
        return None
    if not isinstance(bke_job["num_years"], int):
        return None
    years = int(bke_job["num_years"])
    if years < 1 or years > policy.policy("renew_limit"):
        log(f"BKE-{job_id} num_years failed validation")
        return None
    return years


def get_domain_lists(dom_db):
    ds_list = []
    ns_list = []
    if sql.has_data(dom_db, "ns"):
        ns_list = dom_db["ns"].lower().split(",")

    if sql.has_data(dom_db, "ds"):
        ds_list = [validate.frag_ds(item) for item in dom_db["ds"].upper().split(",")]

    return ns_list, ds_list


def get_dom_from_db(bke_job):
    job_id = bke_job["backend_id"]
    if not check_have_data(job_id, bke_job, ["domain_id"]):
        log(f"BKE-{job_id}: 'domain_id' missing or invalid")
        return None

    domain_id = bke_job["domain_id"]
    table = "deleted_domains" if bke_job["job_type"] == "dom/delete" else "domains"
    ok, dom_db = sql.sql_select_one(table, {"domain_id": int(domain_id)})
    if not ok:
        log(f"BKE-{job_id}: DOM-{domain_id} could not be found in '{table}'")
        return None

    if "name" not in dom_db:
        return None

    name_ok = validate.check_domain_name(dom_db["name"])
    if (not sql.has_data(dom_db, "name")) or (name_ok is not None):
        log(f"BKE-{job_id}: DOM-{domain_id} domain name missing or invalid ({name_ok})")
        return None

    return dom_db


def check_dom_data(job_id, domain, ns_list, ds_list):
    """ Validate the data passed """
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
