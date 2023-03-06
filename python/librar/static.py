#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" fixed data """

import os

POLICY_FILE = os.environ["BASE"] + "/config/policy.json"
PRIORITY_FILE = os.environ["BASE"] + "/config/priority.json"
REGISTRY_FILE = os.environ["BASE"] + "/config/registry.json"
LOGINS_FILE = os.environ["BASE"] + "/config/logins.json"
PAYMENT_FILE = os.environ["BASE"] + "/config/payment.json"
PORTS_LIST_FILE = "/run/regs_ports"

DEFAULT_CURRENCY = {"desc": "US Dollars", "iso": "USD", "separator": [",", "."], "symbol": "$", "decimal": 2}
DEFAULT_NS = "ns1.example.com,ns2.exmaple.com"

HEADER = {'Content-type': 'application/json', 'Accept': 'application/json'}

CLIENT_DOM_FLAGS = ["DeleteProhibited", "RenewProhibited", "TransferProhibited", "UpdateProhibited"]
DOMAIN_ACTIONS = ["create", "renew", "transfer", "restore"]

PAY_TOKEN_SINGLE = 1
PAY_TOKEN_VERIFIED = 2
PAY_TOKEN_CAN_PULL = 3
PAY_TOKEN_USER_ENTERED = 4
PAY_TOKEN_SEEN_SINGLE = 10

STATUS_LIVE = 1
STATUS_WAITING_PAYMENT = 10
STATUS_WAITING_PROCESSING = 11
STATUS_EXPIRED = 20
STATUS_TRANS_QUEUED = 100
STATUS_TRANS_REQ = 101
STATUS_TRANS_FAIL = 120
STATUS_RESERVED = 200

IS_LIVE_STATUS = {1: True}

DOMAIN_STATUS = {
    STATUS_LIVE: "Live",
    STATUS_WAITING_PAYMENT: "Awating Payment",
    STATUS_WAITING_PROCESSING: "Processing",
    STATUS_EXPIRED: "Expired",
    STATUS_TRANS_QUEUED: "Transfer Queued",
    STATUS_TRANS_REQ: "Transfer Requested",
    STATUS_TRANS_FAIL: "Transfer Failed",
    STATUS_RESERVED: "Reserved"
}

POW10 = [
    1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000, 10000000000, 100000000000, 1000000000000
]

NOW_DATE_FIELDS = ["when_dt", "amended_dt", "created_dt", "deleted_dt"]
