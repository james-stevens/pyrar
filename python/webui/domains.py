#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions to handle domains for the UI rest/api """

import sys
import base64

from librar import passwd
from librar.mysql import sql_server as sql
from librar import sigprocs, domobj, misc, pdns, tlsa, static, hashstr, registry, validate

from mailer import spool_email
from backend import libback


def get_domain_prices(domlist, num_years=1, qry_type=None, user_id=None):
    """ get retail prices for Domains in {domlist} """
    if qry_type is None:
        qry_type = ["create", "renew"]

    if not domlist.registry or "type" not in domlist.registry:
        return False, "Registrar not supported"

    ok, prices = libback.get_prices(domlist, num_years, qry_type)
    if not ok or prices is None:
        return False, "Price check failed"

    domlist.load_all()
    dom_dict = {dom["name"]: dom for dom in prices}

    for name, this_domobj in domlist.domobjs.items():
        dom_price = dom_dict[name]
        futher_process_price_item(this_domobj, dom_price, num_years, user_id)

    registry.tld_lib.multiply_values(prices, num_years)
    return True, prices


def futher_process_price_item(this_domobj, dom_price, num_years, user_id):
    if not this_domobj.valid_expiry_limit(num_years):
        for action in static.DOMAIN_ACTIONS:
            if action in dom_price:
                del dom_price[action]
                dom_price[action + ":fail"] = "Renew limit exceeded"

    if this_domobj.dom_db is None:
        return

    dom_db = this_domobj.dom_db

    if "RenewProhibited" in this_domobj.locks and "renew" in dom_price:
        del dom_price["renew"]
        dom_price["renew:fail"] = "Renewal blocked by locks"

    dom_price["avail"] = False
    if dom_db["user_id"] == user_id:
        dom_price["yours"] = True
    dom_price["reason"] = "Already registered"

    if misc.has_data(dom_db, "for_sale_msg"):
        dom_price["avail"] = True
        dom_price["for_sale_msg"] = dom_db["for_sale_msg"]

    if "create" in dom_price:
        del dom_price["create"]


def check_domain_is_mine(user_id, domain, require_live):
    if not misc.has_data(domain, "name") or not validate.is_valid_fqdn(domain["name"]):
        return False, "Domain data missing or invalid"

    dom = domobj.Domain()
    if not dom.load_name(domain["name"], user_id)[0]:
        return False, "Domain not found or not yours"

    if require_live and dom.dom_db["status_id"] not in static.IS_LIVE_STATUS:
        return False, "Operation only supported on live domains"

    return True, dom


def webui_update_domain(req):
    ok, dom = check_domain_is_mine(req.user_id, req.post_js, True)
    if not ok:
        return False, dom

    update_cols = {}

    if "auto_renew" in req.post_js and isinstance(req.post_js["auto_renew"], bool):
        update_cols["auto_renew"] = req.post_js["auto_renew"]

    if not (reply := check_update_ns(req.post_js, dom.dom_db, update_cols))[0]:
        return False, reply[1]

    if not (reply := check_update_ds(req.post_js, dom.dom_db, update_cols))[0]:
        return False, reply[1]

    if not sql.sql_update_one("domains", update_cols, {"domain_id": dom.dom_db["domain_id"], "user_id": req.user_id}):
        return False, "Domain update failed"

    domain_backend_update(dom.dom_db)
    return True, update_cols


def check_update_ns(post_dom, dom_db, update_cols):
    if "ns" not in post_dom or post_dom["ns"] == dom_db["ns"]:
        return True, None

    if not misc.has_data(post_dom, "ns"):
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

    if not misc.has_data(post_dom, "ds"):
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
    if dom_db["status_id"] not in static.IS_LIVE_STATUS:
        return
    bke_job = {
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "job_type": request_type,
        "execute_dt": misc.now(),
        "created_dt": None
    }
    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")


def domain_transfer(req):
    name = req.post_js["name"].lower()
    doms = domobj.DomainList()
    ok, reply = doms.set_list(name)
    if not ok:
        return False, reply
    ok, reply = doms.load_all()
    dom = doms.domobjs[name]

    if not dom.can_transfer:
        return False, "Domain is too young to transfer"

    if ok and len(dom.dom_db) > 0:
        return internal_domain_transfer(req,dom.dom_db)

    ok, prices = get_domain_prices(doms, 1, ["transfer"], req.user_id)
    if not ok:
        return req.abort(prices)

    return True, {"name": dom.name, "tld": dom.tld, "authcode": req.post_js["authcode"], "prices": prices}


def internal_domain_transfer(req,dom_db):
    if dom_db["user_id"] == req.user_id:
        return False, "The domain is already yours"
    if not (misc.has_data(dom_db, "authcode")
            and passwd.compare(req.post_js["authcode"], dom_db["authcode"])):
        return False, "Authcode provided does not match the one on file"

    old_user_id = dom_db["user_id"]
    if sql.sql_update_one("domains", {
            "authcode": None,
            "user_id": req.user_id
    }, {"domain_id": dom_db["domain_id"]}):
        req.event({
            "domain_id": dom_db["domain_id"],
            "notes": "Domain transferred away using correct authcode",
            "event_type": "dom/transfer"
        })
        pdns.delete_zone(dom_db["name"])
        spool_email.spool("transferred_away", [["domains", {
            "domain_id": dom_db["domain_id"]
        }], ["users", {
            "user_id": old_user_id
        }]])
        return True, True
    return False, reply


def webui_set_authcode(req):
    ok, dom = check_domain_is_mine(req.user_id, req.post_js, True)
    if not ok:
        return False, dom

    if not dom.can_transfer:
        return False, "Domain is too young to transfer"

    if "TransferProhibited" in dom.locks:
        return False, "Gifting / Transfer blocked by locks"

    authcode = hashstr.make_hash(f"{req.post_js['name']}.{req.post_js['domain_id']}.{req.sess_code}", 15)
    password = passwd.crypt(authcode)
    sql.sql_update_one("domains", {"authcode": password}, {"domain_id": dom.dom_db["domain_id"]})

    bke_job = {
        "domain_id": dom.dom_db["domain_id"],
        "user_id": req.user_id,
        "job_type": "dom/authcode",
        "authcode": base64.b64encode(authcode.encode("utf-8")).decode("utf-8"),
        "execute_dt": misc.now(),
        "created_dt": None
    }

    sql.sql_insert("backend", bke_job)
    sigprocs.signal_service("backend")

    return True, {"authcode": authcode}


def webui_gift_domain(req):
    ok, dom = check_domain_is_mine(req.user_id, req.post_js, True)
    if not ok:
        return False, dom

    if not dom.can_transfer:
        return False, "Domain is too young to transfer"

    if "TransferProhibited" in dom.locks:
        return False, "Gifting / Transfer blocked by flags"

    if "dest_email" not in req.post_js or not validate.is_valid_email(req.post_js["dest_email"]):
        return False, "Recipient email missing or invalid"

    ok, new_user_db = sql.sql_select_one("users", {"email": req.post_js["dest_email"]})
    if not ok:
        return False, "Recipient email invalid"

    where = {col: req.post_js[col] for col in ["domain_id", "name", "user_id"]}
    if not sql.sql_update_one("domains", {"user_id": new_user_db["user_id"]}, where):
        return False, "Gifting domain failed"

    pdns.delete_from_catalog(dom.dom_db["name"])
    pdns.delete_zone(dom.dom_db["name"])

    spool_email.spool("gifted_domain", [["domains", {
        "domain_id": req.post_js["domain_id"]
    }], ["users", {
        "user_id": new_user_db["user_id"]
    }]])
    return True, {"new_user_id": new_user_db["user_id"]}


def webui_update_domains_flags(req):
    ok, dom = check_domain_is_mine(req.user_id, req.post_js, True)
    if not ok:
        return False, dom

    if not misc.has_data(req.post_js, "flags"):
        return False, "Missing or invalid data"

    new_flags = dom.locks.copy()
    for flag, flag_state in req.post_js["flags"].items():
        if not (isinstance(flag_state, bool) and isinstance(flag, str) and flag in static.CLIENT_DOM_FLAGS):
            return False, "Missing or invalid data"
        if flag not in dom.registry["locks"]:
            return False, f"Flag '{flag}' is not supported in this registry"

        new_flags[flag] = flag_state

    update_flags = ",".join([flag for flag, flag_val in new_flags.items() if flag_val])

    if not sql.sql_update_one("domains", {"client_locks": update_flags}, {
            "domain_id": dom.dom_db["domain_id"],
            "user_id": req.user_id
    }):
        return False, "Domain update failed"

    domain_backend_update(dom.dom_db, "dom/flags")
    return True, {"client_locks": update_flags}


def webui_add_tlsa_record(req):
    ok, dom = check_domain_is_mine(req.user_id, req.post_js, True)
    if not ok:
        return False, dom

    ok, tlsa_data = tlsa.make_tlsa_json(req.post_js)
    if not ok:
        return False, "TLSA Generator failed"

    ok, reply = pdns.update_rrs(dom.dom_db["name"], tlsa_data["tlsa_rr"])
    if not ok:
        return False, reply

    return True, tlsa_data["pem"]


def can_transfer(dom, now=None):
    min_trans_time = dom.registry["domain_transfer_age"] * -86400
    if now is None:
        now = misc.now(min_trans_time)
    return dom.dom_db["created_dt"] < now


def main():
    sql.connect("webui")
    registry.start_up()
    doms = domobj.DomainList()
    doms.set_list(sys.argv[1:])
    doms.load_all()
    for __, d in doms.domobjs.items():
        print(">>>>", d.name, d.can_transfer)


if __name__ == "__main__":
    main()
