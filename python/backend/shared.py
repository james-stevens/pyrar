#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import inspect

from librar.log import log, init as log_init
from librar.policy import this_policy as policy
from librar import mysql as sql
from librar import validate


def do_domain_update(job_id, name, dom_db, epp_info):
    this_reg, url = registry.tld_lib.reg_record_for_domain(name)
    ns_list, ds_list = get_domain_lists(dom_db)
    if not check_dom_data(job_id, name, ns_list, ds_list):
        return None

    add_ns = [item for item in ns_list if item not in epp_info["ns"]]
    del_ns = [item for item in epp_info["ns"] if item not in ns_list]

    add_ds = [ds_data for ds_data in ds_list if not ds_in_list(ds_data, epp_info["ds"])]
    del_ds = [ds_data for ds_data in epp_info["ds"] if not ds_in_list(ds_data, ds_list)]

    if (len(add_ns + del_ns + add_ds + del_ds)) <= 0:
        return True

    if len(add_ns) > 0:
        run_host_create(job_id, this_reg, url, add_ns)


def event_log(notes, bke_job):
    where = inspect.stack()[1]
    event_row = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None,
        "event_type": "BackEnd:" + bke_job["job_type"],
        "domain_id": bke_job["domain_id"],
        "user_id": bke_job["user_id"],
        "who_did_it": "eppsvr",
        "from_where": "localhost",
        "notes": notes
    }
    sql.sql_insert("events", event_row)


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
        log(f"BKE-{job_id}: DOM-'{domain_id}' missing or invalid")
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
