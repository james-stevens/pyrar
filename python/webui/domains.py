#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import re
import base64

from lib import registry
from lib import validate
from lib.policy import this_policy as policy
from lib.log import log, debug, init as log_init
from lib import mysql as sql
from lib import misc
from lib import sigprocs
from lib import parsexml
import users

import handler
from plugins import *


class DomainName:
    def __init__(self, domain):
        self.names = None
        self.err = None
        self.registry = None
        self.client = None
        self.currency = policy.policy("currency")
        if not validate.valid_currency(self.currency):
            log("ERROR: Main policy currency is not set up correctly, using default values")
            self.currency = misc.DEFAULT_CURRENCY

        if isinstance(domain, str):
            if domain.find(",") >= 0:
                self.process_list(domain.split(","))
            else:
                self.process_string(domain)

        if isinstance(domain, list):
            self.process_list(domain)

        if self.registry is None:
            self.err = "TLD not supported"
            self.names = None
        else:
            regs_file = registry.tld_lib.regs_file.data()
            if "currency" in self.registry:
                if validate.valid_currency(self.currency):
                    self.currency = self.registry["currency"]
                else:
                    log(f"ERROR: Registry currency for '{self.registry['name']}' is not set up correctly")

    def process_string(self, domain):
        name = domain.lower()
        if (err := validate.check_domain_name(name)) is None:
            self.names = name
        else:
            self.err = err
            self.names = None
        self.registry = registry.tld_lib.reg_record_for_domain(name)
        if self.registry["type"] == "epp":
            self.client = registry.tld_lib.clients[self.registry["name"]]
        else:
            self.client = None
        self.xmlns = registry.make_xmlns(self.registry)

    def process_list(self, domain):
        self.names = []
        for dom in domain:
            name = dom.lower()
            if (err := validate.check_domain_name(name)) is None:
                self.names.append(name)
                if self.registry is None:
                    self.registry = registry.tld_lib.reg_record_for_domain(name)
                    if self.registry["type"] == "epp":
                        self.client = registry.tld_lib.clients[self.registry["name"]]
                    else:
                        self.client = None
                    self.xmlns = registry.make_xmlns(self.registry)
                else:
                    regs = registry.tld_lib.reg_record_for_domain(name)
                    if regs != self.registry:
                        self.err = "ERROR: Split registry request"
                        self.names = None
                        return
            else:
                self.err = err
                self.names = None
                return


def get_domain_prices(domobj, num_years=1, qry_type=["create", "renew"], user_id=None):
    if not domobj.registry or "type" not in domobj.registry:
        return False, "Registrar not supported"

    if (plugin_func := handler.run(domobj.registry["type"], "dom/price")) is None:
        return False, "No plugin fro this Registrar"

    ok, ret_js = plugin_func(domobj, num_years, qry_type, user_id)
    if not ok or ret_js is None:
        return False, "Price check failed"

    registry.tld_lib.multiply_values(ret_js, num_years)
    registry.tld_lib.sort_data_list(ret_js, is_tld=False)

    return True, ret_js


def close_epp_sess():
    return


def check_domain_is_mine(user_id, domain):
    if not sql.has_data(domain, ["domain_id", "name"]):
        return False, "Domain data missing"

    ok, dom_db = sql.sql_select_one("domains", {
        "domain_id": domain["domain_id"],
        "name": domain["name"],
        "user_id": user_id
    })

    if not ok:
        return False, "Domain not found or not yours"

    return True, dom_db


def webui_update_domain(req, post_dom):
    ok, msg = check_domain_is_mine(req.user_id, post_dom)
    if not ok:
        return False, msg

    update_cols = {}

    if "name_servers" in post_dom:
        if not sql.has_data(post_dom, "name_servers"):
            update_cols["name_servers"] = ""
        else:
            new_ns = post_dom["name_servers"].lower().split(",")
            new_ns.sort()
            for ns in new_ns:
                if not validate.is_valid_fqdn(ns):
                    return False, "Invalid name server record"
            update_cols["name_servers"] = ",".join(new_ns)

    if "ds_recs" in post_dom:
        if not sql.has_data(post_dom, "ds_recs"):
            update_cols["ds_recs"] = ""
        else:
            new_ds = post_dom["ds_recs"].upper().split(",")
            new_ds.sort()
            for ds in new_ds:
                if not validate.is_valid_ds(validate.frag_ds(ds)):
                    return False, "Invalid DS record"
            update_cols["ds_recs"] = ",".join(new_ds)

    ok = sql.sql_update_one("domains", update_cols, {"domain_id": post_dom["domain_id"]})

    if not ok:
        return False, "Domain update failed"

    epp_job = {
        "domain_id": post_dom["domain_id"],
        "user_id": req.user_id,
        "job_type": "dom/update",
        "execute_dt": sql.now(),
        "created_dt": None
    }
    sql.sql_insert("epp_jobs", epp_job)
    sigprocs.signal_service("backend")

    return True, update_cols


def webui_set_auth_code(req, post_dom):
    ok, msg = check_domain_is_mine(req.user_id, post_dom)
    if not ok:
        return False, msg

    auth_code = users.make_session_key(f"{post_dom['name']}.{post_dom['domain_id']}", req.sess_code)
    auth_code = re.sub('[+/=]', '', auth_code)[:15]

    epp_job = {
        "domain_id": post_dom["domain_id"],
        "user_id": req.user_id,
        "job_type": "dom/authcode",
        "authcode": base64.b64encode(auth_code.encode("utf-8")).decode("utf-8"),
        "execute_dt": sql.now(),
        "created_dt": None
    }

    sql.sql_insert("epp_jobs", epp_job)
    sigprocs.signal_service("backend")

    return True, {"auth_code": auth_code}


def webui_gift_domain(req, post_dom):
    ok, msg = check_domain_is_mine(req.user_id, post_dom)
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


class Empty:
    pass


if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("webui")
    # print(">>>>>", set_auth_code(10450, {"domain_id": 10458, "name": "zip1.chug"}))
    user = Empty()
    user.user_id = 10450
    print(
        ">>>>>",
        webui_gift_domain(user, {
            "user_id": user.user_id,
            "dest_email": "fred@frod.com",
            "domain_id": 10458,
            "name": "zip1.chug"
        }))
