#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

HEXLIB = "0123456789ABCDEF"
HEADER = {'Content-type': 'application/json', 'Accept': 'application/json'}

CLIENT_DOM_FLAGS = [
    "DeleteProhibited", "RenewProhibited", "TransferProhibited",
    "UpdateProhibited"
]

DOMAIN_STATUS = {
    1: "Live",
    10: "Awating Payment",
    100: "Transfer Queued",
    101: "Transfer Requested",
    120: "Transfer Failed"
}


def ashex(line):
    ret = ""
    for item in line:
        asc = ord(item)
        ret = ret + HEXLIB[asc >> 4] + HEXLIB[asc & 0xf]
    return ret
