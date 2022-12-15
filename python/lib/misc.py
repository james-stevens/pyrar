#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

HEXLIB = "0123456789ABCDEF"
HEADER = {'Content-type': 'application/json', 'Accept': 'application/json'}
DEFAULT_NS = "ns1.example.com,ns2.exmaple.com"
CLIENT_DOM_FLAGS = ["DeleteProhibited", "RenewProhibited", "TransferProhibited", "UpdateProhibited"]
DEFAULT_CURRENCY = { "iso": "USD", "separator": [",","."], "symbol": "$", "decimal": 2, "pow10" : 100 }

EPP_ACTIONS = ["create", "renew", "transfer", "restore"]

STATUS_LIVE = 1
STATUE_WAITING_PAYMENT = 10
STATUE_TRANS_QUEUED = 100
STATUE_TRANS_REQ = 101
STATUE_TRANS_FAIL = 120

DOMAIN_STATUS = {
    1: "Live",
    10: "Awating Payment",
    100: "Transfer Queued",
    101: "Transfer Requested",
    120: "Transfer Failed"
}


def ashex(line):
    if isinstance(line, str):
        line = line.encode("utf-8")
    ret = ""
    for asc in line:
        ret += HEXLIB[asc >> 4] + HEXLIB[asc & 0xf]
    return ret


if __name__ == "__main__":
    print(ashex("tst"))
    print(ashex("tst".encode("utf-8")))
    print(ashex("🐸tst".encode("utf-8")))
