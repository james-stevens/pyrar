#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
import lib.fileloader as fileloader
import lib.log as log

WEBUI_POLICY = os.environ["BASE"] + "/etc/policy.json"

DEFAULT_CURRENCY = { "iso": "USD", "separator": [",","."], "symbol": "$", "decimal": 2, "pow10" : 100 }
DEFAULT_NS = "ns1.example.com,ns2.exmaple.com"


policy_defaults = {
	"facility_python_code": 170,
	"log_python_code": True,
	"session_timeout": 60,
	"currency": DEFAULT_CURRENCY,
	"facility_epp_api": 170,
	"log_epp_api": True,
	"business_name": "Registry",
	"dnssec_algorithm": "ecdsa256",
	"dnssec_ksk_bits": 256,
	"dnssec_zsk_bits": 256,
	"dns_servers": DEFAULT_NS,
	"catalog_zone":"pyrar.localhost",
	"default_ttl":86400,
	"epp_retry_timeout": 300,
	"epp_retry_attempts": 3,
	"facility_eppsvr": 170,
	"max_renew_years": 10
	}



class Policy:
    def __init__(self):
        self.file = None
        self.file = fileloader.FileLoader(WEBUI_POLICY)

    def policy(self, name, default_value=None):
        our_policy = self.file.data()
        if name in our_policy:
            return our_policy[name]
        if name in policy_defaults:
        	return policy_defaults[name]
        return default_value

    def add_policy(self, key, value):
        self.file.json[key] = value

    def data(self):
        return self.file.data()


this_policy = Policy()

if __name__ == "__main__":
    print(">>>TEST>>>:" , this_policy.policy("business_name"))
    print(">>>TEST>>>:" , this_policy.policy("log_python_code", "Unk"))
    print(">>>TEST>>>:" , this_policy.policy("some_value", "some_def"))
    this_policy.add_policy("some_value", "THIS")
    print(">>>TEST>>>:" , this_policy.policy("some_value", "some_def"))
