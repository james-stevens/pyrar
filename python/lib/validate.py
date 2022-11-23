#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import re

IS_FQDN = r'^([a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}\.)+[a-z0-9]([-a-z0-9]{0,61}[a-z0-9]){0,1}[.]?$'
IS_TLD = r'^[a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}$'
IS_EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{1,}\b'


def is_valid_email(name):
    if name is None or not isinstance(name, str):
        return False
    return re.match(IS_EMAIL, name, re.IGNORECASE) is not None


def is_valid_tld(name):
    if name is None or not isinstance(name, str):
        return False
    if len(name) > 63 or len(name) <= 0:
        return False

    return re.match(IS_TLD, name, re.IGNORECASE) is not None


def is_valid_fqdn(name):
    if name is None or not isinstance(name, str):
        return False
    if len(name) > 255 or len(name) <= 0:
        return False
    return re.match(IS_FQDN, name, re.IGNORECASE) is not None


if __name__ == "__main__":
    for host in ["A_A", "www.gstatic.com.", "m.files.bbci.co.uk."]:
        print(host, "TLD:", is_valid_tld(host), "HOST:", is_valid_fqdn(host))
    for host in sys.argv:
        print(host, "TLD:", is_valid_tld(host), "HOST:", is_valid_fqdn(host))
