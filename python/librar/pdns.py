#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import requests
import json
import time
import secrets
import hashlib
import dns.name

from librar.log import log
from librar import misc
from librar import static_data
from librar.policy import this_policy as policy

client = None
headers = static_data.HEADER
headers["X-API-Key"] = os.environ["PDNS_API_KEY"]

PDNS_BASE_URL = "http://127.0.0.1:8081/api/v1/servers/localhost"


def start_up():
    global client
    client = requests.Session()
    client.headers.update(headers)

    catalog_zone = policy.policy("catalog_zone")
    if not zone_exists(catalog_zone):
        create_zone(catalog_zone,False)


def zone_exists(name):
    return load_zone_keys(name) != None


def hash_zone_name(name):
    """ return {name} FQDN as a catalog hash in text """
    if name[-1] != ".":
        name += "."
    return hashlib.sha1(dns.name.from_text(name).to_wire()).hexdigest().lower()


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
    """ rest/api calls to sign zone called {name}, name must have trailing "." """
    dnssec_algorithm = policy.policy("dnssec_algorithm")
    dnssec_ksk_bits = policy.policy("dnssec_ksk_bits")
    dnssec_zsk_bits = policy.policy("dnssec_zsk_bits")
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


def create_zone(name, with_dnssec=False):
    if name[-1] != ".":
        name += "."

    dns_servers = policy.policy("dns_servers").split(",")
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

    zone_hashed = hash_zone_name(name)
    now = str(int(time.time()))
    catalog_zone = policy.policy("catalog_zone","pyrar.localhost")

    post_json += [{
        "cmd": "PATCH",
        "url": f"{PDNS_BASE_URL}/zones/{name}",
        "data": {
            "rrsets": [{
                "name": f"{name}",
                "ttl": policy.policy("default_ttl",86400),
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

    run_cmds(post_json)
    return load_zone(name)


def unsign_zone(name):
    if name[-1] != ".":
        name += "."

    keys = load_zone_keys(name)

    post_json = [ {
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{name}",
        "data": { "nsec3param":"" },
        } ]

    for key in keys:
        post_json.append({ "cmd":"DELETE", "url":f"{PDNS_BASE_URL}/zones/{name}/cryptokeys/{key['id']}" })

    return run_cmds(post_json)


def run_cmds(post_json):
    ret = True
    for req in post_json:
        json_data = req["data"] if "data" in req else None
        request = requests.Request(req["cmd"],req["url"],json=json_data,headers=headers)
        response = client.send(request.prepare())
        ret = ret and response.status_code >= 200 and response.status_code <= 299
    return ret


def sign_zone(name):
    if name[-1] != ".":
        name += "."
    run_cmds(dnssec_zone_cmds(name))
    return load_zone_keys(name)


def delete_zone(name):
    if name[-1] != ".":
        name += "."

    catalog_zone = policy.policy("catalog_zone")
    zone_hashed = hash_zone_name(name)

    post_json = [ {
        "cmd": "DELETE",
        "url": f"{PDNS_BASE_URL}/zones/{name}"
    } , {
        "cmd": "PATCH",
        "url": f"{PDNS_BASE_URL}/zones/{catalog_zone}.",
        "data": { "rrsets": [ 
            {
            "name": f"{zone_hashed}.zones.{catalog_zone}.",
            "ttl": 3600,
            "type":"PTR",
            "changetype":"REPLACE",
            "records": []
            } ] }
    } , {
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{catalog_zone}./notify"
    } ]

    return run_cmds(post_json)


def update_rrs(zone,rrs):
    if zone[-1] != ".":
        zone += "."

    if "ttl" not in rrs:
        rrs["ttl"] = policy.policy("default_ttl")

    rr_data = { "changetype": "REPLACE", "records": {} }
    for item in ["name","ttl","type"]:
        if item not in rrs:
            return False, f"Missing data item '{item}'"
        rr_data[item] = rrs[item]
    if rr_data["name"][-1] != ".":
        rr_data["name"] += "."

    if "data" in rrs:
        rr_data["records"] = [ { "content":val,"disabled":False} for val in rrs["data"] ]

    resp = client.patch(f"{PDNS_BASE_URL}/zones/{zone}",json={ "rrsets": [ rr_data ] },headers=headers)

    ok = resp.status_code >= 200 and resp.status_code <= 299
    if not ok:
        try:
            js_content = json.loads(resp.content)
            if "error" in js_content:
                err_txt = js_content["error"]
                err_parts = err_txt.split(":")
                if err_txt.find("(try 'pdnsutil check-zone'):") > 0:
                    err_txt = err_parts[0] + "&nbsp;<br>&nbsp;" + err_parts[2]
                else:
                    err_txt = err_parts[0] + "&nbsp;<br>&nbsp;" + err_parts[1]
                return ok, err_txt
        except Exception as e:
            pass
        return ok, "Failed to update"

    return ok, resp



if __name__ == "__main__":
    start_up()
    name="pant.to.glass"
    # print(unsign_zone(name))
    # print("UPDATE>>>",update_rrs(name,{"name":"www.zz","type":"A","data":["1.2.3.4","5.6.5.19"]}))
    # print("KEYS>>>>",load_zone_keys(name))
    # print("CREATE>>>>",json.dumps(create_zone(name, False),indent=3))
    print("KEYS>>>>",load_zone_keys(name))
    # print("EXISTS>>>>",zone_exists(name))
    # print("DELETE>>>>",json.dumps(delete_zone(name)))
    print("EXISTS>>>>",zone_exists(name))
    # print("KEYS>>>>",load_zone_keys(name))
    print("ZONE>>>>",json.dumps(load_zone(name)))
    # print(json.dumps(sign_zone("mine"),indent=3))
    # print(json.dumps(load_zone_keys("mine"),indent=3))
    # print(json.dumps(create_zone("mine", True),indent=3))
