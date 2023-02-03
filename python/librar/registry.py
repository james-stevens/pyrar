#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import random
import requests

from librar import static_data
from librar import fileloader
from librar import mysql as sql
from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy

SEND_REGS_ITEMS = ["max_checks", "desc", "type", "locks", "renew_limit"]
MANDATORY_REGS_ITEMS = ["locks", "renew_limit", "expire_recover_limit", "orders_expire_hrs", "strict_idna2008"]

DEFAULT_XMLNS = {
    "contact": "urn:ietf:params:xml:ns:contact-1.0",
    "domain": "urn:ietf:params:xml:ns:domain-1.0",
    "epp": "urn:ietf:params:xml:ns:epp-1.0",
    "eppcom": "urn:ietf:params:xml:ns:eppcom-1.0",
    "fee": "urn:ietf:params:xml:ns:epp:fee-1.0",
    "host": "urn:ietf:params:xml:ns:host-1.0",
    "loginSec": "urn:ietf:params:xml:ns:epp:loginSec-1.0",
    "org": "urn:ietf:params:xml:ns:epp:org-1.0",
    "orgext": "urn:ietf:params:xml:ns:epp:orgext-1.0",
    "rgp": "urn:ietf:params:xml:ns:rgp-1.0",
    "secDNS": "urn:ietf:params:xml:ns:secDNS-1.1"
}

tld_lib = None


def make_xmlns(registry_data):
    ret_xmlns = DEFAULT_XMLNS
    if "xmlns" in registry_data:
        for xml_name, xml_data in registry_data["xmlns"].items():
            ret_xmlns[xml_name] = xml_data
    return ret_xmlns


def have_newer(mtime, file_name):
    if not os.path.isfile(file_name) or not os.access(file_name, os.R_OK):
        return None

    new_time = os.path.getmtime(file_name)
    if new_time <= mtime:
        return None

    return new_time


def key_priority(item):
    if "priority" in item:
        return item["priority"]
    return 1000


def get_price_from_json(price_json, cls, action):
    if cls in price_json and action in price_json[cls]:
        return price_json[cls][action]
    for item in [f"{cls}.{action}", action, "default"]:
        if item in price_json:
            return price_json[item]
    return None


class ZoneLib:
    def __init__(self):
        self.zone_list = []
        self.zone_data = {}
        self.zone_priority = {}
        self.zones_from_db = []
        self.registry = None
        self.clients = {}

        self.last_zone_table = None
        self.check_zone_table()
        self.logins_file = fileloader.FileLoader(static_data.LOGINS_FILE)
        self.regs_file = fileloader.FileLoader(static_data.REGISTRY_FILE)
        self.priority_file = fileloader.FileLoader(static_data.PRIORITY_FILE)

        self.process_json()

    def check_zone_table(self):
        ok, last_change = sql.sql_select_one("zones", "enabled and allow_sales", "max(amended_dt) 'last_change'")
        if not ok:
            return None

        if self.last_zone_table is not None and self.last_zone_table >= last_change["last_change"]:
            return False

        self.last_zone_table = last_change["last_change"]
        ok, self.zones_from_db = sql.sql_select("zones", "enabled and allow_sales")
        if not ok:
            return None

        self.zone_data = {}
        for row in self.zones_from_db:
            self.zone_data[row["zone"]] = {col: row[col] for col in ["registry", "renew_limit"] if row[col]}
            if sql.has_data(row, "price_info"):
                try:
                    self.zone_data[row["zone"]]["prices"] = json.loads(row["price_info"])
                except ValueError:
                    pass
        return True

    def check_for_new_files(self):
        zones_db_is_new = self.check_zone_table()
        regs_file_is_new = self.regs_file.check()
        priority_file_is_new = self.priority_file.check()

        if regs_file_is_new or priority_file_is_new or zones_db_is_new:
            self.process_json()
            return True

        return False

    def process_json(self):
        with open(static_data.PORTS_LIST_FILE, "r", encoding="UTF-8") as fd:
            port_lines = [line.split() for line in fd.readlines()]
        ports = {p[0]: int(p[1]) for p in port_lines}

        self.zone_priority = {idx: pos for pos, idx in enumerate(self.priority_file.json)}

        self.registry = self.regs_file.json
        for registry, reg_data in self.registry.items():
            for param in MANDATORY_REGS_ITEMS:
                if param not in reg_data:
                    reg_data[param] = policy.policy(param)

            reg_data["name"] = registry
            if reg_data["type"] == "epp" and registry in ports:
                reg_data["url"] = f"http://127.0.0.1:{ports[registry]}/epp/api/v1.0/request"

        for __, zone_rec in self.zone_data.items():
            zone_rec["reg_data"] = self.registry[zone_rec["registry"]]
            if "renew_limit" not in zone_rec or not zone_rec["renew_limit"]:
                zone_rec["renew_limit"] = zone_rec["reg_data"]["renew_limit"]

        new_list = [{"name": dom, "priority": self.tld_priority(dom, is_tld=True)} for dom in self.zone_data]
        self.sort_data_list(new_list, is_tld=True)
        self.zone_list = [dom["name"] for dom in new_list]

        is_epp = {}
        for name, reg_data in self.registry.items():
            if reg_data["type"] == "epp":
                is_epp[name] = True
                if name not in self.clients:
                    self.clients[name] = requests.Session()
        for reg in list(self.clients):
            if reg not in is_epp:
                self.clients[reg].close()
                del self.clients[reg]

    def regs_send(self):
        regs_to_send = {}
        for registry, reg_data in self.registry.items():
            regs_to_send[registry] = {item: reg_data[item] for item in SEND_REGS_ITEMS if item in reg_data}
        return regs_to_send

    def sort_data_list(self, the_list, is_tld=False):
        for dom in the_list:
            if "match" in dom and dom["match"]:
                dom["priority"] = 1
            else:
                dom["priority"] = self.tld_priority(dom["name"], is_tld)

        the_list.sort(key=key_priority)
        for dom in the_list:
            if "priority" in dom:
                del dom["priority"]

    def zone_rec_of_name(self, name):
        if (tld := self.tld_of_name(name)) is None:
            return None
        return self.zone_data[tld]

    def tld_of_name(self, name):
        if (idx := name.find(".")) >= 0:
            return name[idx + 1:]
        if name not in self.zone_data:
            return None
        return name

    def tld_priority(self, name, is_tld=False):
        tld = name
        if not is_tld:
            tld = self.tld_of_name(name)
        if tld is not None and tld in self.zone_priority:
            return self.zone_priority[tld] + 10
        return random.randint(1000, 9999999)

    def url(self, registry):
        return self.registry[registry]["url"]

    def reg_record_for_domain(self, domain):
        if (tld := self.tld_of_name(domain)) is None:
            return None, None
        return self.zone_data[tld]["reg_data"] if "reg_data" in self.zone_data[tld] else None

    def extract_items(self, dom):
        return {
            "priority": self.tld_priority(dom, is_tld=True),
            "name": dom,
            "registry": self.zone_data[dom]["registry"]
        }

    def return_zone_list(self):
        new_list = [self.extract_items(dom) for dom in self.zone_list if dom in self.zone_data]
        new_list.sort(key=key_priority)
        for record in new_list:
            if "priority" in record:
                del record["priority"]
        return new_list

    def supported_tld(self, name):
        if (name is None) or (not isinstance(name, str)) or (name == ""):
            return False
        return self.tld_of_name(name) in self.zone_data

    def get_mulitple(self, this_reg, tld, cls, action):
        if "prices" in self.zone_data[tld]:
            if (ret := get_price_from_json(self.zone_data[tld]["prices"], cls, action)) is not None:
                return ret
        if "prices" in this_reg:
            if (ret := get_price_from_json(this_reg["prices"], cls, action)) is not None:
                return ret
        if (price_policy := policy.policy("prices")) is not None:
            if (ret := get_price_from_json(price_policy, cls, action)) is not None:
                return ret
        return None

    def multiply_values(self, check_dom_data, num_years, retain_reg_price=False):
        for dom in check_dom_data:
            if (tld := self.tld_of_name(dom["name"])) is None:
                return False
            this_reg = self.zone_data[tld]["reg_data"]

            cls = dom["class"].lower() if "class" in dom else "standard"

            for action in static_data.DOMAIN_ACTIONS:
                if action not in dom:
                    continue

                if (factor := self.get_mulitple(this_reg, tld, cls, action)) is None:
                    if action in ["transfer", "restore"] and dom[action] is None or dom[action] == 0:
                        factor = self.get_mulitple(this_reg, tld, cls, "renew")

                if factor is None:
                    del dom[action]
                else:
                    apply_price_factor(action, dom, factor, num_years, retain_reg_price)

        return True


def apply_price_factor(action, dom, factor, num_years, retain_reg_price):
    regs_price = float(dom[action]) if dom[action] is not None else 0
    if isinstance(factor, str):
        if factor[:1] == "x":
            our_price = regs_price * float(factor[1:])
        elif factor[:1] == "+":
            our_price = regs_price + float(factor[1:])
    else:
        our_price = float(factor)

    if dom[action] is None or dom[action] == 0:
        our_price *= float(num_years)

    site_currency = policy.policy("currency")
    our_price *= static_data.POW10[site_currency["decimal"]]
    our_price = round(float(our_price), 0)

    if retain_reg_price:
        regs_price *= static_data.POW10[site_currency["decimal"]]
        regs_price = round(float(regs_price), 0)
        dom["reg_" + action] = int(regs_price)

    dom[action] = int(our_price)


def start_up():
    global tld_lib
    if tld_lib is None:
        tld_lib = ZoneLib()
    else:
        tld_lib.check_for_new_files()


if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("webui")
    start_up()

    dom_data = [{"name": "tiny.zz", "renew": None}]
    tld_lib.multiply_values(dom_data, 12)
    print(dom_data)

    # print(tld_lib.registry)
    # print("REGISTRY", json.dumps(tld_lib.registry, indent=3))
    # print("ZONE_DATA", json.dumps(tld_lib.zone_data, indent=3))
    # print("WHOLE_REG", json.dumps(tld_lib.reg_record_for_domain("fred.of.glass"), indent=3))
    # print("ZONE_LIST", json.dumps(tld_lib.zone_list, indent=3))
    # print("ZONE_SEND", json.dumps(tld_lib.regs_send(), indent=3))
    # print("ZONE_FROM_DB", json.dumps(tld_lib.zones_from_db, indent=3))
    # print("ZONE_PRIORITY", json.dumps(tld_lib.zone_priority, indent=3))
    # print("return_zone_list", json.dumps(tld_lib.return_zone_list(), indent=3))
    # print(json.dumps(tld_lib.return_zone_list(), indent=3))
    # print(json.dumps(tld_lib.make_xmlns(), indent=3))
