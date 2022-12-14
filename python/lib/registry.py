#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import random
from inspect import currentframe as czz, getframeinfo as gzz

from lib import fileloader
from lib import mysql as sql
from lib.log import log, debug, init as log_init
from lib.policy import this_policy as policy

EPP_REST_PRIORITY = os.environ["BASE"] + "/etc/priority.json"
EPP_REGISTRY = os.environ["BASE"] + "/etc/registry.json"
EPP_LOGINS = os.environ["BASE"] + "/etc/logins.json"
EPP_PORTS_LIST = "/run/regs_ports"

DEFAULT_CONFIG = {"max_checks": 5, "desc": "Unknown"}

tld_lib = None


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


def tld_of_name(name):
    if (idx := name.find(".")) >= 0:
        return name[idx + 1:]
    return name


def get_price_from_json(price_json, cls, action):
    if cls in price_json and action in price_json[cls]:
        return price_json[cls][action]
    for item in [f"{cls}.{action}", action, "default"]:
        if item in price_json:
            return price_json[item]
    return None


class ZoneLib:
    def __init__(self):
        self.zone_send = {}
        self.zone_list = []
        self.zone_data = {}
        self.zone_priority = {}
        self.registry = None

        self.last_zone_table = None
        self.check_zone_table()
        self.logins_file = fileloader.FileLoader(EPP_LOGINS)
        self.regs_file = fileloader.FileLoader(EPP_REGISTRY)
        self.priority_file = fileloader.FileLoader(EPP_REST_PRIORITY)

        with open(EPP_PORTS_LIST, "r", encoding="UTF-8") as fd:
            port_lines = [line.split() for line in fd.readlines()]
        self.ports = {p[0]: int(p[1]) for p in port_lines}

        self.process_json()

    def check_zone_table(self):
        ok, last_change = sql.sql_select_one("zones", None, "max(amended_dt) 'last_change'")
        if not ok:
            return None

        if self.last_zone_table is not None and self.last_zone_table >= last_change["last_change"]:
            return False

        self.last_zone_table = last_change["last_change"]
        ok, zone_from_db = sql.sql_select("zones", None, "zone,registry,price_info")
        if not ok:
            return None

        self.zone_data = {}
        for row in zone_from_db:
            self.zone_data[row["zone"]] = {"registry": row["registry"]}
            if sql.has_data(row, "price_info"):
                try:
                    self.zone_data[row["zone"]]["prices"] = json.loads(row["price_info"])
                except ValueError as e:
                    continue
        return True

    def check_for_new_files(self):
        zones_db_is_new = self.check_zone_table()
        regs_file_is_new = self.regs_file.check()
        priority_file_is_new = self.priority_file.check()

        if regs_file_is_new or priority_file_is_new or zones_db_is_new:
            self.process_json()

    def process_json(self):
        self.zone_priority = {idx: pos for pos, idx in enumerate(self.priority_file.json)}
        new_send = {}
        self.registry = self.regs_file.json
        for registry, reg_data in self.registry.items():
            new_send[registry] = {}
            for item, val in DEFAULT_CONFIG.items():
                new_send[registry][item] = reg_data[item] if item in reg_data else val
            reg_data["name"] = registry
            if reg_data["type"] == "epp":
                port = self.ports[registry]
                reg_data["url"] = f"http://127.0.0.1:{port}/epp/api/v1.0/request"

        self.zone_send = new_send
        new_list = [{"name": dom, "priority": self.tld_priority(dom, is_tld=True)} for dom in self.zone_data]
        self.sort_data_list(new_list, is_tld=True)
        self.zone_list = [dom["name"] for dom in new_list]

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

    def tld_priority(self, name, is_tld=False):
        tld = name
        if not is_tld:
            tld = tld_of_name(name)
        if tld in self.zone_priority:
            return self.zone_priority[tld] + 10
        return random.randint(1000, 9999999)

    def url(self, registry):
        return self.registry[registry]["url"]

    def http_req(self, domain):
        tld = tld_of_name(domain)
        if tld not in self.zone_data:
            return None, None
        this_reg = self.zone_data[tld]["registry"]

        return self.registry[this_reg] if this_reg in self.registry else None

    def extract_items(self, dom):
        return {
            "priority": self.tld_priority(dom, is_tld=True),
            "name": dom,
            "registry": self.zone_data[dom]["registry"]
        }

    def return_zone_list(self):
        new_list = [self.extract_items(dom) for dom in self.zone_list if dom in self.zone_data]
        new_list.sort(key=key_priority)
        return new_list

    def supported_tld(self, name):
        if (name is None) or (not isinstance(name, str)) or (name == ""):
            return False
        return tld_of_name(name) in self.zone_data

    def get_mulitple(self, this_reg, tld, cls, action):
        if "prices" in self.zone_data[tld]:
            if (ret := get_price_from_json(self.zone_data[tld]["prices"], cls, action)) is not None:
                return ret
        if "prices" in this_reg:
            if (ret := get_price_from_json(this_reg["prices"], cls, action)) is not None:
                return ret
        if (price_policy := policy.policy("prices", None)) is not None:
            if (ret := get_price_from_json(price_policy, cls, action)) is not None:
                return ret
        return None

    def multiply_values(self, check_dom_data, num_years):
        for dom in check_dom_data:
            tld = tld_of_name(dom["name"])
            reg_name = self.zone_data[tld]["registry"]
            this_reg = self.registry[reg_name] if reg_name in self.registry else None

            cls = dom["class"].lower() if "class" in dom else "standard"

            for action in ["create", "renew", "transfer", "restore"]:
                if action not in dom:
                    continue

                if action in ["transfer","restore"] and this_reg["type"] == "local":
                    action = "renew"

                if (mul := self.get_mulitple(this_reg, tld, cls, action)) is None:
                    del dom[action]
                    continue

                if isinstance(mul, str):
                    if mul[:1] == "x":
                        val = float(dom[action]) * float(mul[1:])
                    elif mul[:1] == "+":
                        val = float(dom[action]) + float(mul[1:])
                else:
                    val = float(mul)

                if this_reg["type"] == "local":
                    val *= float(num_years)

                val = round(float(val), 2)
                dom[action] = f'{val:.2f}'

    def make_xmlns(self):
        default_xmlns = {
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
        ret_xmlns = {}
        for registry, data in self.registry.items():
            ret_xmlns[registry] = default_xmlns
            if "xmlns" in data:
                for xml_name, xml_data in data["xmlns"].items():
                    ret_xmlns[registry][xml_name] = xml_data
        return ret_xmlns


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

    # print(tld_lib.registry)
    print("REGISTRY", json.dumps(tld_lib.registry, indent=3))
    print("ZONE_DATA", json.dumps(tld_lib.zone_data, indent=3))
    print("ZONE_LIST", json.dumps(tld_lib.zone_list, indent=3))
    print("ZONE_PRIORITY", json.dumps(tld_lib.zone_priority, indent=3))
    print("return_zone_list", json.dumps(tld_lib.return_zone_list(), indent=3))
    # print("PORTS", json.dumps(tld_lib.ports, indent=3))
    # print(json.dumps(tld_lib.return_zone_list(), indent=3))
    # print(json.dumps(tld_lib.make_xmlns(), indent=3))
