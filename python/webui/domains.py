#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions to handle domains for the UI rest/api """

import sys
import json
import base64

from librar import registry
from librar import validate
from librar.log import log
from librar import mysql as sql
from librar import sigprocs
from librar import domobj
from librar import static_data
from librar import hashstr

from mailer import spool_email

from backend import dom_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from backend.dom_plugins import *


def get_domain_prices(domlist, num_years=1, qry_type=None, user_id=None):
    """ get retail prices for Domains in {domlist} """
    if qry_type is None:
        qry_type = ["create", "renew"]

    if not domlist.registry or "type" not in domlist.registry:
        return False, "Registrar not supported"

    if (plugin_func := dom_handler.run(domlist.registry["type"], "dom/price")) is None:
        return False, f"No plugin for this Registrar '{domlist.registry['name']}/{domlist.registry['type']}'"

    ok, prices = plugin_func(domlist, num_years, qry_type)
    if not ok or prices is None:
        return False, "Price check failed"

    domlist.load_all()
    dom_dict = {dom["name"]: dom for dom in prices}

    for name, this_domobj in domlist.domobjs.items():
        dom_price = dom_dict[name]

        if not this_domobj.valid_expiry_limit(num_years):
            for action in static_data.EPP_ACTIONS:
                if action in dom_price:
                    del dom_price[action]
                    dom_price[action + ":fail"] = "Renew limit exceeded"

        if this_domobj.dom_db is None:
            continue
        dom_db = this_domobj.dom_db

        current_flags = {}
        if sql.has_data(dom_db, "client_locks"):
            current_flags = {flag: True for flag in dom_db["client_locks"].split(",")}
        if "RenewProhibited" in current_flags and "renew" in dom_price:
            del dom_price["renew"]
            dom_price["renew:fail"] = "Renewal blocked by flags"

        dom_price["avail"] = False
        if dom_db["user_id"] == user_id:
            dom_price["yours"] = True
        dom_price["reason"] = "Already registered"

        if sql.has_data(dom_db, "for_sale_msg"):
            dom_price["avail"] = True
            dom_price["for_sale_msg"] = dom_db["for_sale_msg"]

        if "create" in dom_price:
            del dom_price["create"]

    registry.tld_lib.multiply_values(prices, num_years)
    return True, prices


def check_domain_is_mine(user_id, domain, require_live):
    if (not sql.has_data(domain, ["domain_id", "name"]) or not isinstance(domain["domain_id"], int)
            or not validate.is_valid_fqdn(domain["name"])):
        return False, "Domain data missing or invalid"

    ok, dom_db = sql.sql_select_one("domains", {
        "domain_id": int(domain["domain_id"]),
        "name": domain["name"],
        "user_id": int(user_id)
    })

    if not ok or not dom_db or len(dom_db) <= 0:
        return False, "Domain not found or not yours"

    if require_live and dom_db["status_id"] not in static_data.LIVE_STATUS:
        return False, "Not live yet"

    return True, dom_db


def webui_update_domain(req):
    if not (reply := check_domain_is_mine(req.user_id, req.post_js, False))[0]:
        return False, reply[1]
    dom_db = reply[1]

    update_cols = {}

    if "auto_renew" in req.post_js and isinstance(req.post_js["auto_renew"], bool):
        update_cols["auto_renew"] = req.post_js["auto_renew"]

    if not (reply := check_update_ns(req.post_js, dom_db, update_cols))[0]:
        return False, reply[1]

    if not (reply := check_update_ds(req.post_js, dom_db, update_cols))[0]:
        return False, reply[1]

    if not sql.sql_update_one("domains", update_cols, {"domain_id": dom_db["domain_id"], "user_id": req.user_id}):
        return False, "Domain update failed"

    if dom_db["status_id"] not in static_data.LIVE_STATUS:
        return True, update_cols

    domain_backend_update(dom_db)
    return True, update_cols


def check_update_ns(post_dom, dom_db, update_cols):
    if "ns" not in post_dom or post_dom["ns"] == dom_db["ns"]:
        return True, None

    if not sql.has_data(post_dom, "ns"):
        update_cols["ns"] = ""
        return True, None

    new_ns = post_dom["ns"].lower().split(",")
    for each_ns in new_ns:
        if not validate.is_valid_fqdn(each_ns):
            return False, "Invalid name server record"
    new_ns.sort()
    update_cols["ns"] = ",".join(new_ns)
    return True, None


def check_update_ds(post_dom, dom_db, update_cols):
    if "ds" not in post_dom or post_dom["ds"] == dom_db["ds"]:
        return True, None

    if not sql.has_data(post_dom, "ds"):
        update_cols["ds"] = ""
        return True, None

    new_ds = post_dom["ds"].upper().split(",")
    for each_ds in new_ds:
        if not validate.is_valid_ds(validate.frag_ds(each_ds)):
            return False, "Invalid DS record"
    new_ds.sort()
    update_cols["ds"] = ",".join(new_ds)
    return True, None


def domain_backend_update(dom_db, request_type="dom/update"):
    bke_job = {
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "job_type": request_type,
        "execute_dt": sql.now(),
        "created_dt": None
    }

    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")


def webui_set_auth_code(req):
    if not (reply := check_domain_is_mine(req.user_id, req.post_js, True))[0]:
        return False, reply[1]
    dom_db = reply[1]

    current_flags = {}
    if sql.has_data(dom_db, "client_locks"):
        current_flags = {flag: True for flag in dom_db["client_locks"].split(",")}
    if "TransferProhibited" in current_flags:
        return False, "Gifting / Transfer blocked by flags"

    auth_code = hashstr.make_hash(f"{req.post_js['name']}.{req.post_js['domain_id']}.{req.sess_code}", 15)

    bke_job = {
        "domain_id": dom_db["domain_id"],
        "user_id": req.user_id,
        "job_type": "dom/authcode",
        "authcode": base64.b64encode(auth_code.encode("utf-8")).decode("utf-8"),
        "execute_dt": sql.now(),
        "created_dt": None
    }

    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")

    return True, {"auth_code": auth_code}


def webui_gift_domain(req):
    if not (reply := check_domain_is_mine(req.user_id, req.post_js, True))[0]:
        return False, reply[1]
    dom_db = reply[1]

    current_flags = {}
    if sql.has_data(dom_db, "client_locks"):
        current_flags = {flag: True for flag in dom_db["client_locks"].split(",")}
    if "TransferProhibited" in current_flags:
        return False, "Gifting / Transfer blocked by flags"

    if "dest_email" not in req.post_js or not validate.is_valid_email(req.post_js["dest_email"]):
        return False, "Recipient email missing or invalid"

    if not (reply := sql.sql_select_one("users", {"email": req.post_js["dest_email"]}))[0]:
        return False, "Recipient email invalid"
    user_db = reply[1]

    where = {col: req.post_js[col] for col in ["domain_id", "name", "user_id"]}
    if not sql.sql_update_one("domains", {"user_id": user_db["user_id"]}, where):
        return False, "Gifting domain failed"

    spool_email.spool("gifted_domain", [["domains", {
        "domain_id": req.post_js["domain_id"]
    }], ["users", {
        "user_id": user_db["user_id"]
    }]])
    return True, {"new_user_id": user_db["user_id"]}


def webui_update_domains_flags(req):
    if not (reply := check_domain_is_mine(req.user_id, req.post_js, True))[0]:
        return False, reply[1]
    dom_db = reply[1]

    if not (sql.has_data(req.post_js, ["flag", "state"]) and isinstance(req.post_js["state"], bool)
            and req.post_js["flag"] in static_data.CLIENT_DOM_FLAGS):
        return False, "Missing or invalid data"

    dom = domobj.Domain()
    dom.set_name(req.post_js["name"])
    this_flag = req.post_js["flag"]
    if this_flag not in dom.registry["locks"]:
        return False, f"Flag '{this_flag}' is not supported in this registry"

    current_flags = {}
    if sql.has_data(dom_db, "client_locks"):
        current_flags = {flag: True for flag in dom_db["client_locks"].split(",")}

    current_flags[this_flag] = req.post_js["state"]
    new_flags = ",".join([flag for flag, flag_val in current_flags.items() if flag_val])

    if not sql.sql_update_one("domains", {"client_locks": new_flags}, {
            "domain_id": dom_db["domain_id"],
            "user_id": req.user_id
    }):
        return False, "Domain update failed"

    domain_backend_update(dom_db, "dom/flags")
    return True, {"client_locks": new_flags}


if __name__ == "__main__":
    sql.connect("webui")
    registry.start_up()
    my_domlist = domobj.DomainList()
    my_domlist.set_list(sys.argv[1:])
    print(json.dumps(get_domain_prices(my_domlist, 11, ["create", "renew"], 10450), indent=3))
