#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json

from lib import parsexml
from lib import mysql as sql
from lib import misc

import handler


def http_price_domains(domobj, years, qry_type):

    if domobj.registry is None or "url" not in domobj.registry:
        return 400, "Unsupported TLD"

    xml = xml_check_with_fees(domobj, years, qry_type)
    resp = domobj.client.post(domobj.registry["url"], json=xml, headers=misc.HEADER)

    if resp.status_code < 200 or resp.status_code > 299:
        return 400, "Invalid HTTP Response from parent"

    try:
        ret_js = json.loads(resp.content)
        return 200, ret_js
    except ValueError as err:
        log(f"{resp.status_code} === {resp.content.decode('utf8')}")
        log(f"**** JSON FAILED TO PARSE ***** {err}")
        return 400, "Returned JSON Parse Error"

    return 400, "Unexpected Error"


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

    return True, ret_js


def xml_check_with_fees(domobj, years, qry_type):
    fees_extra = [fees_one(name, years) for name in qry_type]
    return {
        "check": {
            "domain:check": {
                "@xmlns:domain": domobj.xmlns["domain"],
                "domain:name": domobj.names
            }
        },
        "extension": {
            "fee:check": {
                "@xmlns:fee": domobj.xmlns["fee"],
                "fee:currency": domobj.currency["iso"],
                "fee:command": fees_extra
            }
        }
    }


def fees_one(action, years):
    return {
        "@name": action,
        "fee:period": {
            "@unit": "y",
            "#text": str(years),
        }
    }


handler.add_plugin("epp", { "dom/price": epp_domain_prices } )
