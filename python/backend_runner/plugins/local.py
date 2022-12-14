#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import shared
import handler

from lib.log import log, debug, init as log_init
from inspect import currentframe as czz, getframeinfo as gzz

from lib import mysql as sql
from lib import registry
from lib import pdns

def domain_create(epp_job,dom_db):
    return domain_update_from_db(epp_job,dom_db)


def start_up_check():
    pdns.start_up()
    return True


def domain_update_from_db(epp_job,dom_db):
    job_id = epp_job["epp_job_id"]
    name = dom_db["name"]

    if (tld := registry.tld_lib.tld_of_name(name)) is None:
        return False

    rrs = { "name":name,"type":"NS","data":[]}
    if sql.has_data(dom_db,"name_servers"):
        rrs["data"] = [ d+"." for d in dom_db["name_servers"].split(",") ]

    ok_ns = pdns.update_rrs(tld,rrs)

    rrs = { "name":name,"type":"DS","data":[]}
    if sql.has_data(dom_db,"ds_recs"):
        rrs["data"] = dom_db["ds_recs"].split(",")

    ok_ds = pdns.update_rrs(tld,rrs)

    return ok_ns and ok_ds


def domain_request_transfer(epp_job,dom_db):
    return True


def domain_renew(epp_job,dom_db):
    return True


def set_authcode(epp_job,dom_db):
    return True


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
