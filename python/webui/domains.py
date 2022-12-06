#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json
import httpx
from inspect import currentframe as czz, getframeinfo as gzz

from lib.registry import tld_lib
from lib import validate
from lib.policy import this_policy as policy
from lib.log import log, debug, init as log_init
from lib import misc
import parsexml


class DomainName:
    def __init__(self, domain):
        self.names = None
        self.err = None
        self.registry = None
        self.url = None
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
            regs_file = tld_lib.regs_file.data()
            if "currency" in regs_file[self.registry]:
                self.currency = regs_file[self.registry]["currency"]

    def process_string(self, domain):
        name = domain.lower()
        if (err := validate.check_domain_name(name)) is None:
            self.names = name
        else:
            self.err = err
            self.names = None
        self.registry, self.url = tld_lib.http_req(name)

    def process_list(self, domain):
        self.names = []
        for dom in domain:
            name = dom.lower()
            if (err := validate.check_domain_name(name)) is None:
                self.names.append(name)
                if self.registry is None:
                    self.registry, self.url = tld_lib.http_req(name)
                else:
                    regs, __ = tld_lib.http_req(name)
                    if regs != self.registry:
                        self.err = "ERROR: Split registry request"
                        self.names = None
                        return
            else:
                self.err = err
                self.names = None
                return


def http_price_domains(domobj, years, which):

    if domobj.registry is None or domobj.url is None:
        return 400, "Unsupported TLD"

    resp = clients[domobj.registry].post(domobj.url,
                                         json=xml_check_with_fees(
                                             domobj, years, which),
                                         headers=misc.HEADER)

    if resp.status_code < 200 or resp.status_code > 299:
        return 400, "Invalid HTTP Response from parent"

    try:
        return 200, json.loads(resp.content)
    except ValueError as err:
        log(f"{resp.status_code} === {resp.content.decode('utf8')}",
            gzz(czz()))
        log(f"**** JSON FAILED TO PARSE ***** {err}", gzz(czz()))
        return 400, "Returned JSON Parse Error"

    return 400, "Unexpected Error"


def check_and_parse(domobj, num_years=1, qry_type=["create", "renew"]):
    ret, out_js = http_price_domains(domobj, num_years, qry_type)
    if ret != 200:
        return abort(ret, out_js)

    print(">>>>>>",json.dumps(out_js,indent=3))
    xml_p = parsexml.XmlParser(out_js)
    code, ret_js = xml_p.parse_check_message()

    if not code == 1000:
        return abort(400, ret_js)

    tld_lib.multiply_values(ret_js)
    tld_lib.sort_data_list(ret_js, is_tld=False)

    return json.dumps(ret_js)


def close_epp_sess():
    for client in clients:
        clients[client].close()


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
                "@xmlns:domain": xmlns[domobj.registry]["domain"],
                "domain:name": domobj.names
            }
        },
        "extension": {
            "fee:check": {
                "@xmlns:fee": xmlns[domobj.registry]["fee"],
                "fee:currency": domobj.currency,
                "fee:command": fees_extra
            }
        }
    }


clients = {p: httpx.Client() for p in tld_lib.ports}
xmlns = tld_lib.make_xmlns()


def check_one_domain(domain):
    domobj = DomainName(domain)
    if domobj.names is None:
        print(">>>>>", domobj.err)
        sys.exit(1)

    ret, out_js = http_price_domains(
        domobj, 1, ["create", "renew", "transfer", "restore"])

    print(">>>> REPLY", ret, out_js)

    if ret != 200:
        log(f"ERROR: {ret} {out_js}", gzz(czz()))
    else:
        xml_p = parsexml.XmlParser(out_js)
        code, ret_js = xml_p.parse_check_message()
        if code == 1000:
            tld_lib.multiply_values(ret_js)
        print(">>>TEST>>>", code, json.dumps(ret_js, indent=3))


if __name__ == "__main__":
    log_init(debug=True)
    if len(sys.argv) > 1:
        x = sys.argv[1].lower()
        print("====>> RUN ONE", x, "=>", sys.argv[1])
        check_one_domain(x)
    else:
        check_one_domain("tiny.for.men")
    close_epp_sess()
