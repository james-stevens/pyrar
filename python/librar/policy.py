#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" manage policy values """

import json

from librar import static
from librar import fileloader

policy_defaults = {
    "smtp_tls_security_level": "may",
    "locks": static.CLIENT_DOM_FLAGS,
    "default_theme": "dark",
    "orders_expire_days": 21,
    "create_expire_days": 7,
    "strict_idna2008": False,
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
    "currency": static.DEFAULT_CURRENCY,
    "facility_epp_api": "local0",
    "log_epp_api": True,
    "business_name": "Registry",
    "dnssec_algorithm": "ecdsa256",
    "dnssec_ksk_bits": 256,
    "dnssec_zsk_bits": 256,
    "dns_servers": static.DEFAULT_NS,
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
    """ policy values manager """
    def __init__(self):
        self.file = fileloader.FileLoader(static.POLICY_FILE)
        self.all_data = None
        self.merge_policy_data()

    def merge_policy_data(self):
        self.all_data = policy_defaults.copy()
        self.all_data.update(self.file.data())

    def check_file(self):
        if self.file.check_for_new():
            self.merge_policy_data()

    def policy(self, name, default_value=None):
        self.check_file()
        return self.all_data[name] if name in self.all_data else default_value

    def data(self):
        self.check_file()
        return self.all_data


this_policy = Policy()

if __name__ == "__main__":
    print(">>>TEST>>>:", this_policy.policy("orders_expire_hrs"))
    print(">>>TEST>>>:", this_policy.policy("business_name"))
    print(">>>TEST>>>:", this_policy.policy("log_python_code", "Unk"))
    print(">>>TEST>>>:", this_policy.policy("some_value", "some_def"))
    print(">>>TEST>>>:", this_policy.policy("some_value", "some_def"))
    print(json.dumps(this_policy.data(), indent=3))
