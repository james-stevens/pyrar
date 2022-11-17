#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import random
import fileloader

EPP_REST_PRIORITY = os.environ["BASE"] + "/etc/priority.json"
EPP_REST_ZONES = os.environ["BASE"] + "/etc/providers.json"
EPP_PORTS_LIST = "/run/prov_ports"


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


class ZoneLib:
    def __init__(self):
        self.zone_json = {}
        self.zone_list = []
        self.zone_data = {}
        self.zone_priority = {}

        self.zone_file = fileloader.FileLoader(EPP_REST_ZONES)
        self.priority_file = fileloader.FileLoader(EPP_REST_PRIORITY)

        self.check_for_new_files()

        with open(EPP_PORTS_LIST, "r", encoding="UTF-8") as fd:
            port_lines = [line.split() for line in fd.readlines()]
        self.ports = {p[0]: int(p[1]) for p in port_lines}

    def check_for_new_files(self):
        self.zone_json, z_is_new = self.zone_file.data()
        self.pri_json, p_is_new = self.priority_file.data()

        if z_is_new or p_is_new:
            self.zone_priority = {
                idx: pos
                for pos, idx in enumerate(self.pri_json)
            }
            self.process_json()

    def process_json(self):
        new_data = {}
        for provider, prov in self.zone_json.items():
            if "domains" in prov:
                doms = prov["domains"]
                for dom in doms:
                    if doms[dom] is None:
                        doms[dom] = {}
                new_data.update({
                    dom: (doms[dom] | {
                        "provider": provider
                    })
                    for dom in doms
                })

        self.zone_data = new_data
        new_list = [{
            "name": dom,
            "priority": self.tld_priority(dom, is_tld=True)
        } for dom in self.zone_data]
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

    def url(self, provider):
        port = self.ports[provider]
        return f"http://127.0.0.1:{port}/epp/api/v1.0/request"

    def http_req(self, domain):
        tld = tld_of_name(domain)
        if tld not in self.zone_data:
            return None, None
        provider = self.zone_data[tld]["provider"]

        if provider not in self.ports:
            return None, None

        return provider, self.url(provider)

    def extract_items(self, dom):
        return {
            "priority": self.tld_priority(dom, is_tld=True),
            "name": dom,
            "provider": self.zone_data[dom]["provider"]
        }

    def return_zone_list(self):
        new_list = [
            self.extract_items(dom) for dom in self.zone_list
            if dom in self.zone_data
        ]
        new_list.sort(key=key_priority)
        return new_list

    def supported_tld(self, name):
        if (name is None) or (not isinstance(name, str)) or (name == ""):
            return False
        return tld_of_name(name) in self.zone_data

    def get_mulitple(self, tld, cls, action):
        tld_data = self.zone_data[tld]
        cls_both = cls + "." + action
        default_both = "default." + action

        if cls_both in tld_data:
            return tld_data[cls_both]

        if cls in tld_data:
            return tld_data[cls]

        if default_both in tld_data:
            return tld_data[default_both]

        if "default" in tld_data:
            return tld_data["default"]

        if "provider" in tld_data:
            if (ret := self.get_prov_mulitple(tld, cls, action)) is not None:
                return ret

        return 2

    def get_prov_mulitple(self, tld, cls, action):
        tld_data = self.zone_data[tld]
        cls_both = cls + "." + action
        default_both = "default." + action

        prov = tld_data["provider"]
        if prov not in self.zone_json:
            return None

        json_prov = self.zone_json[prov]
        if "prices" not in json_prov:
            return None

        if cls_both in json_prov["prices"]:
            return json_prov["prices"][cls_both]

        if cls in json_prov["prices"]:
            return json_prov["prices"][cls]

        if default_both in json_prov["prices"]:
            return json_prov["prices"][default_both]

        return json_prov["prices"]["default"] if "default" in json_prov[
            "prices"] else None

    def multiply_values(self, data):

        for dom in data:
            tld = tld_of_name(dom["name"])

            cls = dom["class"].lower() if "class" in dom else "standard"

            for itm in ["create", "renew", "transfer", "restore"]:
                if itm in dom:
                    mul = self.get_mulitple(tld, cls, itm)
                    if mul[:1] == "x":
                        val = float(dom[itm]) * float(mul[1:])
                    else:
                        val = float(mul)
                    val = round(float(val), 2)
                    dom[itm] = f'{val:.2f}'

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
        for provider, data in self.zone_json.items():
            ret_xmlns[provider] = default_xmlns
            if "xmlns" in data:
                for xml_name, xml_data in data["xmlns"].items():
                    ret_xmlns[provider][xml_name] = xml_data
        return ret_xmlns


if __name__ == "__main__":
    my_zone_lib = ZoneLib()
    # print(my_zone_lib.zone_json)
    print("ZONE_DATA", json.dumps(my_zone_lib.zone_data, indent=3))
    print("ZONE_LIST", json.dumps(my_zone_lib.zone_list, indent=3))
    print("ZONE_PRIORITY", json.dumps(my_zone_lib.zone_priority, indent=3))
    print("PORTS", json.dumps(my_zone_lib.ports, indent=3))
    # print(json.dumps(my_zone_lib.return_zone_list(), indent=3))
    # print(json.dumps(my_zone_lib.make_xmlns(), indent=3))
