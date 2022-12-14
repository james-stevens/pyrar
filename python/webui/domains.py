#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import httpx
import re
import base64
from inspect import currentframe as czz, getframeinfo as gzz

from lib import registry
from lib import validate
from lib.policy import this_policy as policy
from lib.log import log, debug, init as log_init
from lib import mysql as sql
from lib import misc
import parsexml
import users

xmlns = None


def start_up():
    global xmlns
    xmlns = registry.tld_lib.make_xmlns()
    for name, reg in registry.tld_lib.registry.items():
        if reg["type"] == "epp":
            reg["client"] = httpx.Client()


class DomainName:
    def __init__(self, domain):
        self.names = None
        self.err = None
        self.registry = None
        self.currency = policy.policy("currency_iso", "USD")

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
                self.currency = self.registry["currency"]

    def process_string(self, domain):
        name = domain.lower()
        if (err := validate.check_domain_name(name)) is None:
            self.names = name
        else:
            self.err = err
            self.names = None
        self.registry = registry.tld_lib.http_req(name)

    def process_list(self, domain):
        self.names = []
        for dom in domain:
            name = dom.lower()
            if (err := validate.check_domain_name(name)) is None:
                self.names.append(name)
                if self.registry is None:
                    self.registry = registry.tld_lib.http_req(name)
                else:
                    regs = registry.tld_lib.http_req(name)
                    if regs != self.registry:
                        self.err = "ERROR: Split registry request"
                        self.names = None
                        return
            else:
                self.err = err
                self.names = None
                return


def http_price_domains(domobj, years, which):

    if domobj.registry is None or "url" not in domobj.registry:
        return 400, "Unsupported TLD"

    resp = domobj.registry["client"].post(domobj.registry["url"],
                                          json=xml_check_with_fees(domobj, years, which),
                                          headers=misc.HEADER)

    if resp.status_code < 200 or resp.status_code > 299:
        return 400, "Invalid HTTP Response from parent"

    try:
        return 200, json.loads(resp.content)
    except ValueError as err:
        log(f"{resp.status_code} === {resp.content.decode('utf8')}", gzz(czz()))
        log(f"**** JSON FAILED TO PARSE ***** {err}", gzz(czz()))
        return 400, "Returned JSON Parse Error"

    return 400, "Unexpected Error"


def get_domain_prices(domobj, num_years=1, qry_type=["create", "renew"], user_id=None):
    if domobj.registry["type"] == "epp":
        return epp_domain_prices(domobj, num_years, qry_type, user_id)

    if domobj.registry["type"] == "local":
        return local_domain_prices(domobj, num_years, qry_type, user_id)

    return False, f"We should not be here '{domobj.registry['type']}'"


def local_domain_prices(domobj, num_years=1, qry_type=["create", "renew"], user_id=None):
    ok, reply = sql.sql_select("domains", {"name": domobj.names})
    if not ok:
        return False, "Unexpected database error"

    dom_as_dict = {dom["name"]: dom for dom in reply}
    ret_js = []
    for dom in domobj.names if isinstance(domobj.names, list) else [domobj.names]:
        add_dom = {"num_years": num_years, "name": dom, "avail": False}
        if dom not in dom_as_dict:
            add_dom["avail"] = True
            for qt in qry_type:
                add_dom[qt] = num_years
        else:
            if sql.has_data(dom_as_dict[dom], "for_sale_msg"):
                add_dom["avail"] = True
                add_dom["for_sale_msg"] = dom_as_dict[dom]["for_sale_msg"]

        ret_js.append(add_dom)

    registry.tld_lib.multiply_values(ret_js, num_years)
    registry.tld_lib.sort_data_list(ret_js, is_tld=False)

    return True, ret_js


def epp_domain_prices(domobj, num_years=1, qry_type=["create", "renew"], user_id=None):
    ok, out_js = http_price_domains(domobj, num_years, qry_type)
    if ok != 200:
        return False, out_js

    xml_p = parsexml.XmlParser(out_js)
    code, ret_js = xml_p.parse_check_message()

    if not code == 1000:
        return False, ret_js

    for item in ret_js:
        if "avail" in item and not item["avail"]:
            ok, reply = sql.sql_select_one("domains", {"name": item["name"]})
            if (ok and len(reply) > 0 and sql.has_data(reply, "for_sale_msg")
                    and (user_id is None or user_id != reply["user_id"])):
                for i in ["user_id", "for_sale_msg"]:
                    item[i] = reply[i]

    registry.tld_lib.multiply_values(ret_js, num_years)
    registry.tld_lib.sort_data_list(ret_js, is_tld=False)

    return True, ret_js


def close_epp_sess():
    for name, reg in registry.tld_lib.registry.items():
        if reg["type"] == "epp":
            reg["client"].close()


def fees_one(action, years):
    return {
        "@name": action,
        "fee:period": {
            "@unit": "y",
            "#text": str(years),
        }
    }


def xml_check_with_fees(domobj, years, which):
    fees_extra = [fees_one(name, years) for name in which]
    return {
        "check": {
            "domain:check": {
                "@xmlns:domain": xmlns[domobj.registry["name"]]["domain"],
                "domain:name": domobj.names
            }
        },
        "extension": {
            "fee:check": {
                "@xmlns:fee": xmlns[domobj.registry["name"]]["fee"],
                "fee:currency": domobj.currency,
                "fee:command": fees_extra
            }
        }
    }


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
        if not has_data(post_dom,"name_servers"):
            update_cols["name_servers"] = None
        else
            new_ns = post_dom["name_servers"].lower().split(",")
            new_ns.sort()
            for ns in new_ns:
                if not validate.is_valid_fqdn(ns):
                    return False, "Invalid name server record"
            update_cols["name_servers"] = ",".join(new_ns)

    if "ds_recs" in post_dom:
        if not sql.has_data(post_dom, "ds_recs"):
            update_cols["ds_recs"] = None
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
        "job_type": "dom/update",
        "execute_dt": sql.now(),
        "created_dt": None
    }
    sql.sql_insert("epp_jobs", epp_job)

    return True, update_cols


def webui_set_auth_code(req, post_dom):
    ok, msg = check_domain_is_mine(req.user_id, post_dom)
    if not ok:
        return False, msg

    auth_code = users.make_session_key(f"{post_dom['name']}.{post_dom['domain_id']}", req.sess_code)
    auth_code = re.sub('[+/=]', '', auth_code)[:15]

    epp_job = {
        "domain_id": post_dom["domain_id"],
        "job_type": "dom/authcode",
        "authcode": base64.b64encode(auth_code.encode("utf-8")).decode("utf-8"),
        "execute_dt": sql.now(),
        "created_dt": None
    }
    sql.sql_insert("epp_jobs", epp_job)
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
    log_init(debug=True)
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
