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
    if len(code) != 86:
        return False
    try:
        base64.b64decode(code + "==")
    except binascii.Error as exc:
        return False
    return True


def frag_ds(ds_data):
    items = ds_data.split(" ")
    if len(items) < 4:
        return None
    return {
        "keyTag":items[0],
        "alg":items[1],
        "digestType":items[2],
        "digest": ds_data[ds_data.find(items[3]):].replace(" ","").upper()
        }


def is_valid_ds(ds_rec):
    if not ds_rec["keyTag"].isdigit() or not ds_rec["alg"].isdigit() or not ds_rec["digestType"].isdigit():    
        return False

    if len(ds_rec["keyTag"]) > 5 or len(ds_rec["alg"]) > 2 or len(ds_rec["digestType"]) > 1:
        return False

    key_tag = int(ds_rec["keyTag"])
    if key_tag < 0 or key_tag > 65536:
        return False

    alg = int(ds_rec["alg"])
    if alg < 1 or alg > 20 or alg in [4,9,11]:
        return False

    digest_tp = int(ds_rec["digestType"])
    if digest_tp not in [1,2,3,4]:
        return False

    for ch in ds_rec["digest"]:
        if ch not in misc.HEXLIB:
            return False

    if {1:40,2:64,3:64,4:96}[digest_tp] != len(ds_rec["digest"]):
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
        print(x, is_valid_ds(frag_ds(x)))

