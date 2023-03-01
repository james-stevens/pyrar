#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" parse EPP JSON """

import json
import sys


class XmlParser:
    def __init__(self, js_inp):
        self.ret_js = {}
        self.js_inp = js_inp

    def parse_check_message(self):
        ret_code, msg = self.get_ret_code()
        if ret_code > 1000:
            return ret_code, msg

        if "resData" not in self.js_inp:
            return 3000, "resData is missing"

        if "domain:chkData" not in self.js_inp["resData"]:
            return 3001, "domain:chkData is missing"

        if "domain:cd" not in self.js_inp["resData"]["domain:chkData"]:
            return 3002, "domain:cd is missing"

        if isinstance(self.js_inp["resData"]["domain:chkData"]["domain:cd"], list):
            for dom_item in self.js_inp["resData"]["domain:chkData"]["domain:cd"]:
                self.parse_one_dom_cd(dom_item)
        else:
            self.parse_one_dom_cd(self.js_inp["resData"]["domain:chkData"]["domain:cd"])

        if ("extension" in self.js_inp) and ("fee:chkData" in self.js_inp["extension"]) and (
                "fee:cd" in self.js_inp["extension"]["fee:chkData"]):

            if isinstance(self.js_inp["extension"]["fee:chkData"]["fee:cd"], list):
                for dom_fee in self.js_inp["extension"]["fee:chkData"]["fee:cd"]:
                    self.parse_one_fee_cd(dom_fee)
            else:
                self.parse_one_fee_cd(self.js_inp["extension"]["fee:chkData"]["fee:cd"])

        return 1000, [(dta | {"name": idx}) for idx, dta in self.ret_js.items()]

    def get_ret_code(self):
        if "result" in self.js_inp and "@code" in self.js_inp["result"]:
            res = self.js_inp["result"]
            msg = "No message given"
            if "extValue" in res and "reason" in res["extValue"]:
                msg = res["extValue"]["reason"]
            elif "msg" in res:
                msg = res["msg"]

            if "@code" in res:
                msg = res["@code"] + ": " + msg

            return int(res["@code"]), msg

        return 5000, "No message"

    def parse_one_dom_cd(self, dom_item):
        if "domain:name" not in dom_item or "#text" not in dom_item["domain:name"]:
            return

        dom_detail = dom_item["domain:name"]
        dom_name = dom_detail["#text"]

        self.ret_js[dom_name] = {"avail": int(dom_detail["@avail"]) == 1 if "@avail" in dom_detail else False}
        if "domain:reason" in dom_item:
            self.ret_js[dom_name]["reason"] = dom_item["domain:reason"]

    def fee_command_one(self, ret_dom, fee_item):
        if "fee:period" in fee_item and "#text" in fee_item["fee:period"]:
            ret_dom["num_years"] = int(fee_item["fee:period"]["#text"])
        if "@name" in fee_item:
            if "fee:fee" in fee_item and "#text" in fee_item["fee:fee"]:
                ret_dom[fee_item["@name"]] = fee_item["fee:fee"]["#text"]
            elif "fee:reason" in fee_item:
                ret_dom[fee_item["@name"] + ":err"] = fee_item["fee:reason"]

    def parse_one_fee_cd(self, dom_fee):
        if "fee:objID" not in dom_fee or "fee:command" not in dom_fee:
            return

        dom = dom_fee["fee:objID"]
        ret_dom = self.ret_js[dom]

        ret_dom["class"] = dom_fee["fee:class"].lower() if "fee:class" in dom_fee else "standard"

        if isinstance(dom_fee["fee:command"], list):
            for fee_item in dom_fee["fee:command"]:
                self.fee_command_one(ret_dom, fee_item)
        else:
            self.fee_command_one(ret_dom, dom_fee["fee:command"])


if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding='UTF-8') as fd:
        js_data = json.load(fd)

    xml_p = XmlParser(js_data)
    ret, out = xml_p.parse_check_message()

    if ret == 1000:
        print(json.dumps(out, indent=2))
    else:
        print("ERROR:", ret, out)
