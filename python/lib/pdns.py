#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import httpx
import json
import time
import secrets

from lib import misc
from lib.policy import this_policy as policy

headers = {"X-API-Key": os.environ["PDNS_API_KEY"]}
client = httpx.Client(headers=headers)

PDNS_BASE_URL = "http://127.0.0.1:8081/api/v1/servers/localhost"

dnssec_algorithm = policy.policy("dnssec_algorithm", "ecdsa256")
dnssec_ksk_bits = policy.policy("dnssec_ksk_bits", 256)
dnssec_zsk_bits = policy.policy("dnssec_zsk_bits", 256)


def load_zone(name):
    if name[-1] != ".":
        name += "."
    resp = client.get(f"{PDNS_BASE_URL}/zones/{name}")
    if resp.status_code < 200 or resp.status_code > 299:
        return None
    return json.loads(resp.content)


def load_zone_keys(name):
    if name[-1] != ".":
        name += "."
    resp = client.get(f"{PDNS_BASE_URL}/zones/{name}/cryptokeys")
    if resp.status_code < 200 or resp.status_code > 299:
        return None
    return json.loads(resp.content)


def dnssec_zone_cmds(name):
    nsec3param = misc.ashex(secrets.token_bytes(6))
    return [{
        "cmd": "POST",
        "url": f"{PDNS_BASE_URL}/zones/{name}/cryptokeys",
        "data": {
            "keytype": "ksk",
            "active": True,
            "algorithm": f"{dnssec_algorithm}",
            "bits": dnssec_ksk_bits
        }
    }, {
        "cmd": "POST",
        "url": f"{PDNS_BASE_URL}/zones/{name}/cryptokeys",
        "data": {
            "keytype": "zsk",
            "active": True,
            "algorithm": f"{dnssec_algorithm}",
            "bits": dnssec_zsk_bits
        }
    }, {
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{name}",
        "data": {
            "nsec3param": f"1 1 5 {nsec3param}"
        }
    }, {
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{name}/rectify"
    }]


def check_zone(name, with_dnssec=False):
    if (ret := load_zone(name)) is not None:
        return ret
    if name[-1] != ".":
        name += "."

    dns_servers = policy.policy("dns_servers", misc.DEFAULT_NS).split(",")
    for idx, ns in enumerate(dns_servers):
        if ns[-1] != ".":
            dns_servers[idx] += "."

    post_json = [{
        "cmd": "POST",
        "url": f"{PDNS_BASE_URL}/zones",
        "data": {
            "name": name,
            "kind": "Master",
            "masters": [],
            "nameservers": dns_servers,
            "soa_edit_api": "EPOCH"
        }
    }]

    if with_dnssec:
        post_json += dnssec_zone_cmds(name)

    zone_hashed = "NOT-RIGHT"
    catalog_zone = "pyrar.localhost"
    now = str(int(time.time()))
    post_json += [{
        "cmd": "PATCH",
        "url": f"{PDNS_BASE_URL}/zones/{name}",
        "data": {
            "rrsets": [{
                "name": f"{name}",
                "ttl": 86400,
                "type": "SOA",
                "changetype": "REPLACE",
                "records": [{
                    "content": f"{dns_servers[0]} hostmaster.{name} {now} 10800 3600 604800 3600",
                    "disabled": False
                }]
            }]
        }
    }, {
        "cmd": "POST",
        "url": f"{PDNS_BASE_URL}/zones/{name}/metadata",
        "data": {
            "type": "Metadata",
            "kind": "SOA-EDIT-DNSUPDATE",
            "metadata": ["EPOCH"]
        }
    }, {
        "cmd": "PATCH",
        "url": f"{PDNS_BASE_URL}/zones/{catalog_zone}.",
        "data": {
            "rrsets": [{
                "name": f"{zone_hashed}.zones.{catalog_zone}.",
                "ttl": 3600,
                "type": "PTR",
                "changetype": "REPLACE",
                "records": [{
                    "content": f"{name}",
                    "disabled": False
                }]
            }]
        }
    }, {
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{name}/notify"
    }]

    for req in post_json:
        json_data = req["data"] if "data" in req else None
        request = client.build_request(req["cmd"],req["url"],json=json_data)
        response = client.send(request)

    return load_zone(name)


if __name__ == "__main__":
    print(json.dumps(load_zone_keys("mine"),indent=3))
    #print(json.dumps(check_zone("mine", True),indent=3))
