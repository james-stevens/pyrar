#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os

POLICY_FILE = os.environ["BASE"] + "/etc/policy.json"
PRIORITY_FILE = os.environ["BASE"] + "/etc/priority.json"
REGISTRY_FILE = os.environ["BASE"] + "/etc/registry.json"
LOGINS_FILE = os.environ["BASE"] + "/etc/logins.json"
PORTS_LIST_FILE = "/run/regs_ports"

DEFAULT_CURRENCY = {"desc": "US Dollars", "iso": "USD", "separator": [",", "."], "symbol": "$", "decimal": 2}
DEFAULT_NS = "ns1.example.com,ns2.exmaple.com"

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

POW10 = [
    1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000, 10000000000, 100000000000, 1000000000000
]
