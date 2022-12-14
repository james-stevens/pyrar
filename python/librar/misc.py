#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import inspect
import idna

LOGINS_JSON = f"{os.environ['BASE']}/etc/logins.json"

HEXLIB = "0123456789ABCDEF"
HEADER = {'Content-type': 'application/json', 'Accept': 'application/json'}

CLIENT_DOM_FLAGS = ["DeleteProhibited", "RenewProhibited", "TransferProhibited", "UpdateProhibited"]
EPP_ACTIONS = ["create", "renew", "transfer", "restore"]

STATUS_LIVE = 1
STATUS_WAITING_PAYMENT = 10
STATUS_WAITING_PROCESSING = 11
STATUS_EXPIRED = 20
STATUS_TRANS_QUEUED = 100
STATUS_TRANS_REQ = 101
STATUS_TRANS_FAIL = 120

LIVE_STATUS = {1: True}

DOMAIN_STATUS = {
    1: "Live",
    10: "Awating Payment",
    11: "Processing",
    20: "Expired",
    100: "Transfer Queued",
    101: "Transfer Requested",
    120: "Transfer Failed"
}


def where_event_log():
    where = inspect.stack()[2]
    return {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None
    }


def ashex(line):
    if isinstance(line, str):
        line = line.encode("utf-8")
    ret = ""
    for asc in line:
        ret += HEXLIB[asc >> 4] + HEXLIB[asc & 0xf]
    return ret


def puny_to_utf8(name,strict_idna_2008=False):
    try:
        idn = idna.decode(name)
        return idn
    except idna.IDNAError as e:
        if strict_idna_2008:
            return None
        try:
            idn = name.encode("utf-8").decode("idna")
            return idn
        except UnicodeError as e:
            return None
    return None



if __name__ == "__main__":
    print(puny_to_utf8("frog.xn--k3h"))
    print(puny_to_utf8("frog.xn--k3hw410f"))
    print(puny_to_utf8("xn--e28h.xn--dp8h"))
    print(puny_to_utf8("xn--strae-oqa.com"))

    print(puny_to_utf8("frog.xn--k3h",True))
    print(puny_to_utf8("frog.xn--k3hw410f",True))
    print(puny_to_utf8("xn--e28h.xn--dp8h",True))
    print(puny_to_utf8("xn--strae-oqa.com",True))
    print(puny_to_utf8("xn--st-rae-oqa.com",True))
