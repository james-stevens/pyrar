#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions to handle domains for the UI rest/api """

import sys
import json
import re
import base64

from librar import registry
from librar import validate
from librar.policy import this_policy as policy
from librar.log import log
from librar import mysql as sql
from librar import sigprocs
from librar import misc
from librar import domobj

from backend import dom_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from backend.dom_plugins import *

from webui import users


def get_domain_prices(domlist, num_years=1, qry_type=None, user_id=None):
    """ get retail prices for Domains in {domlist} """
    if qry_type is None:
        qry_type = ["create", "renew"]

    if not domlist.registry or "type" not in domlist.registry:
        return False, "Registrar not supported"

    if (plugin_func := dom_handler.run(domlist.registry["type"], "dom/price")) is None:
        return False, f"No plugin for this Registrar '{domlist.registry['name']}/{domlist.registry['type']}'"

    ok, ret_js = plugin_func(domlist, num_years, qry_type)
    if not ok or ret_js is None:
        return False, "Price check failed"

    domlist.load_all()
    local_doms = { name:domobj.dom_db for name, domobj in domlist.domobjs.items() if domobj.dom_db is not None }
    dom_dict = { dom["name"]:dom for dom in ret_js }

    for name, domobj in domlist.domobjs.items():
        if domobj.dom_db is None:
            continue

        this_dom = dom_dict[name]
        this_dom["avail"] = False
        if domobj.dom_db["user_id"] == user_id:
            this_dom["yours"] = True
        this_dom["reason"] = "Already registered"
        if sql.has_data(domobj.dom_db, "for_sale_msg"):
            this_dom["avail"] = True
            this_dom["for_sale_msg"] = domobj.dom_db["for_sale_msg"]
        if "create" in this_dom:
            del this_dom["create"]

    registry.tld_lib.multiply_values(ret_js, num_years)
    return True, ret_js


def check_domain_is_mine(user_id, domain, require_live):
    if (not sql.has_data(domain, ["domain_id", "name"]) or not isinstance(domain["domain_id"], int)
            or not validate.is_valid_fqdn(domain["name"])):
        return False, "Domain data missing or invalid"

    ok, dom_db = sql.sql_select_one("domains", {
        "domain_id": int(domain["domain_id"]),
        "name": domain["name"],
        "user_id": int(user_id)
    })

    if not ok:
        return False, "Domain not found or not yours"

    if require_live and dom_db["status_id"] not in misc.LIVE_STATUS:
        return False, "Not live yet"

    return True, dom_db


def webui_update_domain(req, post_dom):
    ok, dom_db = check_domain_is_mine(req.user_id, post_dom, False)
    if not ok:
        return False, dom_db

    update_cols = {}

    if "auto_renew" in post_dom and isinstance(post_dom["auto_renew"], bool):
        update_cols["auto_renew"] = post_dom["auto_renew"]

    ok, reply = check_update_ns(post_dom, dom_db, update_cols)
    if not ok:
        return ok, reply

    ok, reply = check_update_ds(post_dom, dom_db, update_cols)
    if not ok:
        return ok, reply

    ok = sql.sql_update_one("domains", update_cols, {"domain_id": post_dom["domain_id"], "user_id": req.user_id})

    if not ok:
        return False, "Domain update failed"

    if dom_db["status_id"] not in misc.LIVE_STATUS:
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


def domain_backend_update(dom_db):
    bke_job = {
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "job_type": "dom/update",
        "execute_dt": sql.now(),
        "created_dt": None
    }

    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")


def webui_set_auth_code(req, post_dom):
    ok, msg = check_domain_is_mine(req.user_id, post_dom, True)
    if not ok:
        return False, msg

    auth_code = users.make_session_key(f"{post_dom['name']}.{post_dom['domain_id']}", req.sess_code)
    auth_code = re.sub('[+/=]', '', auth_code)[:15]

    bke_job = {
        "domain_id": post_dom["domain_id"],
        "user_id": req.user_id,
        "job_type": "dom/authcode",
        "authcode": base64.b64encode(auth_code.encode("utf-8")).decode("utf-8"),
        "execute_dt": sql.now(),
        "created_dt": None
    }

    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")

    return True, {"auth_code": auth_code}


def webui_gift_domain(req, post_dom):
    ok, msg = check_domain_is_mine(req.user_id, post_dom, True)
    if not ok:
        return False, msg

    if "dest_email" not in post_dom or not validate.is_valid_email(post_dom["dest_email"]):
        return False, "Recipient email missing or invalid"

    ok, user_db = sql.sql_select_one("users", {"email": post_dom["dest_email"]})
    if not ok:
        return False, "Recipient email invalid"

    where = {col: post_dom[col] for col in ["domain_id", "name", "user_id"]}
    ok = sql.sql_update_one("domains", {"user_id": user_db["user_id"]}, where)

    if not ok:
        return False, "Gifting domain failed"

    return ok, {"new_user_id": user_db["user_id"]}


if __name__ == "__main__":
    sql.connect("webui")
    registry.start_up()
    domlist = domobj.DomainList()
    domlist.set_list(sys.argv[1:])
    print(json.dumps(get_domain_prices(domlist,1,["create","renew"],10450),indent=3))
