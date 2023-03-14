#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" code to run validations """

import binascii
import base64
import sys
import re

from librar import registry
from librar import misc
from librar import static

IS_HOST = r'^(\*\.|)([\_a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}\.)+[a-z0-9]([-a-z0-9]{0,61}[a-z0-9]){0,1}[.]?$'
IS_FQDN = r'^([a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}\.)+[a-z0-9]([-a-z0-9]{0,61}[a-z0-9]){0,1}[.]?$'
IS_TLD = r'^[a-z0-9]([-a-z-0-9]{0,61}[a-z0-9]){0,1}[.]?$'
IS_EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{1,}\b'

MAX_DS_LEN = {"keyTag": 5, "alg": 2, "digestType": 1}
MAX_DS_VAL = {"keyTag": 65535, "alg": 20, "digestType": 4}
VALID_DS_LEN = {1: 40, 2: 64, 3: 64, 4: 96}

VALID_RR_TYPES = {
    "A": True,
    "A6": True,
    "AAAA": True,
    "ADDR": True,
    "AFSDB": True,
    "ALIAS": True,
    "ATMA": True,
    "CAA": True,
    "CDNSKEY": True,
    "CDS": True,
    "CERT": True,
    "CNAME": True,
    "DHCID": True,
    "DLV": True,
    "DNAME": True,
    "DNSKEY": True,
    "DS": True,
    "EID": True,
    "EUI48": True,
    "EUI64": True,
    "GPOS": True,
    "HINFO": True,
    "IPSECKEY": True,
    "ISDN": True,
    "KEY": True,
    "KX": True,
    "LOC": True,
    "LUA": True,
    "MAILA": True,
    "MAILB": True,
    "MB": True,
    "MD": True,
    "MF": True,
    "MG": True,
    "MINFO": True,
    "MR": True,
    "MX": True,
    "NAPTR": True,
    "NIMLOC": True,
    "NS": True,
    "NSAP": True,
    "NSAP_PTR": True,
    "NULL": True,
    "NXT": True,
    "OPENPGPKEY": True,
    "OPT": True,
    "PTR": True,
    "PX": True,
    "RKEY": True,
    "RP": True,
    "RRSIG": True,
    "RT": True,
    "SIG": True,
    "SMIMEA": True,
    "SOA": True,
    "SPF": True,
    "SRV": True,
    "SSHFP": True,
    "TKEY": True,
    "TLSA": True,
    "TXT": True,
    "URI": True,
    "WKS": True,
    "WKS ": True,
    "X25": True
}


def has_idn(name):
    if name[:4] == 'xn--':
        return True
    if name.find(".xn--") > 0:
        return True
    return False


def valid_rr_type(rr_type):
    return rr_type in VALID_RR_TYPES


def check_domain_name(name):
    if not registry.tld_lib.supported_tld(name):
        return "Unsupported TLD"
    if not is_valid_fqdn(name):
        return "Domain failed validation"
    return None


def is_valid_display_name(name):
    if len(name.split(" ")) > 4:
        return False
    for illegal in "\\/:%=&'\";)({}#][<>\n\t":
        if name.find(illegal) >= 0:
            return False
    return all(name.find(illegal) < 0 for illegal in ['--', '..'])


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
    if re.match(IS_FQDN, name, re.IGNORECASE) is None:
        return False
    if has_idn(name) and misc.puny_to_utf8(name) is None:
        return False
    return True


def is_valid_hostname(name):
    if name is None or not isinstance(name, str):
        return False
    if len(name) > 255 or len(name) <= 0:
        return False
    return re.match(IS_HOST, name, re.IGNORECASE) is not None


def is_valid_ses_code(code):
    if len(code) != 44:
        return False
    try:
        base64.b64decode(code)
    except binascii.Error:
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
    if ds_rec is None:
        return False
    ints = {}
    for item in ["keyTag", "alg", "digestType"]:
        if not ds_rec[item].isdigit() or len(ds_rec[item]) > MAX_DS_LEN[item]:
            return False

        ints[item] = int(ds_rec[item])
        if ints[item] > MAX_DS_VAL[item] or ints[item] < 1:
            return False

    if ints["alg"] in [4, 9, 11]:
        return False

    if VALID_DS_LEN[ints["digestType"]] != len(ds_rec["digest"]):
        return False

    return re.fullmatch(r'^[0-9a-fA-F]+$', ds_rec["digest"])


def validate_binary(val):
    if not isinstance(val, int):
        return False
    return val in [0, 1]


def is_valid_pin(val):
    return len(val) == 4 and val.isdecimal()


def valid_currency(currency):
    for item in ["iso", "symbol", "separator", "decimal", "desc"]:
        if item not in currency:
            return False

    if len(currency["iso"]) != 3:
        return False

    if not isinstance(currency["decimal"], int):
        return False

    return True


def valid_domain_actions(actions):
    for action in actions:
        if action not in static.DOMAIN_ACTIONS:
            return False
    return len(actions) > 0


def valid_float(num):
    try:
        ret = float(num)
        return ret
    except ValueError:
        return None
    return None


def valid_email_opt_out(email_opt_out):
    return True


def main():
    # for host in ["A_A", "www.gstatic.com.", "m.files.bbci.co.uk."]:
    #     print(host, "TLD:", is_valid_tld(host), "HOST:", is_valid_fqdn(host))
    del sys.argv[0]
    # for host in sys.argv:
    #     print(host, "TLD:", is_valid_tld(host), "HOST:", is_valid_fqdn(host))
    # code = "CLLGnM7+xqKvhHmi5sfIIuszEHuqhVxNbV1IHGRVYZtuTkFC6mHUucxU/gSd5U/cExZrsdu9rRK7d0VtY1bW2g"
    # print("SESS",code,is_valid_ses_code(code))
    # for code in sys.argv:
    #     print("SESS",code,is_valid_ses_code(code))
    for item in sys.argv:
        print(item, is_valid_hostname(item))


if __name__ == "__main__":
    main()
