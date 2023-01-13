#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
from librar import fileloader
import librar.log as log

WEBUI_POLICY = os.environ["BASE"] + "/etc/policy.json"

DEFAULT_CURRENCY = {"desc": "US Dollars", "iso": "USD", "separator": [",", "."], "symbol": "$", "decimal": 2}
DEFAULT_NS = "ns1.example.com,ns2.exmaple.com"

policy_defaults = {
    "strict_referrer": True,
    "pdns_log_facility": 0,
    "pdns_log_level": 5,
    "website_name": "https://example.com/",
    "name_sender": "Customer Support",
    "email_sender": "support@example.com",
    "email_return": "no_reply@example.com",
    "facility_backend": "local0",
    "facility_python_code": "local0",
    "log_python_code": True,
    "session_timeout": 60,
    "webui_sessions": 5,
    "admin_sessions": 3,
    "currency": DEFAULT_CURRENCY,
    "facility_epp_api": "local0",
    "log_epp_api": True,
    "business_name": "Registry",
    "dnssec_algorithm": "ecdsa256",
    "dnssec_ksk_bits": 256,
    "dnssec_zsk_bits": 256,
    "dns_servers": DEFAULT_NS,
    "catalog_zone": "pyrar.localhost",
    "default_ttl": 86400,
    "backend_retry_timeout": 300,
    "backend_retry_attempts": 3,
    "renew_limit": 10,
    "max_basket_size": 10,
    "trans_per_page": 25,
    "orders_expire_hrs": int(6.5 * 24),
    "expire_recover_limit": 30,
    "auto_renew_before": 14,
    "renewal_reminders": "30,14,7"
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
    print(">>>TEST>>>:", this_policy.policy("orders_expire_hrs"))
    print(">>>TEST>>>:", this_policy.policy("business_name"))
    print(">>>TEST>>>:", this_policy.policy("log_python_code", "Unk"))
    print(">>>TEST>>>:", this_policy.policy("some_value", "some_def"))
    this_policy.add_policy("some_value", "THIS")
    print(">>>TEST>>>:", this_policy.policy("some_value", "some_def"))
