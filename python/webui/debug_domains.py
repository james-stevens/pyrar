#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import httpx

import domains
from librar import parsexml
from librar import mysql as sql
from librar.log import log, debug, init as log_init
from librar import misc


def debug_one_domain(domain):
    domobj = domains.DomainName(domain)
    if domobj.names is None:
        print(">>>>>", domobj.err)
        sys.exit(1)

    ok, out_js = http_price_domains(domobj, 1, misc.EPP_ACTIONS)

    print(">>>> REPLY", ok, out_js)

    if ok != 200:
        log(f"ERROR: {ok} {out_js}")
    else:
        xml_p = parsexml.XmlParser(out_js)
        code, ret_js = xml_p.parse_check_message()
        if code == 1000:
            tld_lib.multiply_values(ret_js, 1)
        print(">>>TEST>>>", code, json.dumps(ret_js, indent=3))


if __name__ == "__main__":
    log_init(debug=True)
    sql.connect("webui")

    print(
        ">>>>>",
        domains.webui_update_domain(10450, {
            "domain_id": 10458,
            "name": "zip1.chug",
            "name_servers": "ns239.dns.com,ns139.dns.com"
        }))

    sys.exit(0)
    if len(sys.argv) > 1:
        x = sys.argv[1].lower()
        print("====>> RUN ONE", x, "=>", sys.argv[1])
        debug_one_domain(x)
    else:
        debug_one_domain("tiny.for.men")
    domains.close_epp_sess()
