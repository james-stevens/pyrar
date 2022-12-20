#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

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
