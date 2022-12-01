#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import binascii
import base64
import sys
import re

from lib.providers import tld_lib

from lib import misc

IS_FQDN = r'^([a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}\.)+[a-z0-9]([-a-z0-9]{0,61}[a-z0-9]){0,1}[.]?$'
IS_TLD = r'^[a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}$'
IS_EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{1,}\b'

MAX_DS_LEN = {"keyTag": 5, "alg": 2, "digestType": 1}
MAX_DS_VAL = {"keyTag": 65535, "alg": 20, "digestType": 4}
VALID_DS_LEN = {1: 40, 2: 64, 3: 64, 4: 96}


def check_domain_name(name):
    if not tld_lib.supported_tld(name):
        return "Unsupported TLD"
    if not is_valid_fqdn(name):
        return "Domain failed validation"
    return None


def is_valid_display_name(name):
    if len(name.split(" ")) > 3:
        return False
    for illegal in "\\/:%=&'\";)({}#][<>\n\t":
        if name.find(illegal) >= 0:
            return False
    for illegal in ["--", ".."]:
        if name.find(illegal) >= 0:
            return False
    return True


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


def is_valid_ses_code(code):
    if len(code) != 44:
        return False
    try:
        base64.b64decode(code)
    except binascii.Error as exc:
        return False
    return True


def frag_ds(ds_data):
    items = ds_data.split(" ")
    if len(items) < 4:
        return None
    data = {"keyTag": items[0], "alg": items[1], "digestType": items[2]}
    del items[0:3]
    data["digest"] = "".join(items).replace(" ", "").upper()
    return data


def is_valid_ds(ds_rec):
    ints = {}
    for item in ["keyTag", "alg", "digestType"]:
        if not ds_rec[item].isdigit() or len(ds_rec[item]) > MAX_DS_LEN[item]:
            return False

        ints[item] = int(ds_rec[item])
        if ints[item] > MAX_DS_VAL[item] or ints[item] < 1:
            return False

    if ints["alg"] in [4, 9, 11]:
        return False

    for ch in ds_rec["digest"]:
        if ch not in misc.HEXLIB:
            return False

    if VALID_DS_LEN[ints["digestType"]] != len(ds_rec["digest"]):
        return False

    return True


if __name__ == "__main__":
    # for host in ["A_A", "www.gstatic.com.", "m.files.bbci.co.uk."]:
    #     print(host, "TLD:", is_valid_tld(host), "HOST:", is_valid_fqdn(host))
    del sys.argv[0]
    # for host in sys.argv:
    #     print(host, "TLD:", is_valid_tld(host), "HOST:", is_valid_fqdn(host))
    # code = "CLLGnM7+xqKvhHmi5sfIIuszEHuqhVxNbV1IHGRVYZtuTkFC6mHUucxU/gSd5U/cExZrsdu9rRK7d0VtY1bW2g"
    # print("SESS",code,is_valid_ses_code(code))
    # for code in sys.argv:
    #     print("SESS",code,is_valid_ses_code(code))
    for x in sys.argv:
        print(">>>>>", x, frag_ds(x))
        print(x, is_valid_ds(frag_ds(x)))
