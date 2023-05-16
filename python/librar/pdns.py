#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions for talking to PowerDNS """

import os
import sys
import json
import time
import secrets
import hashlib
import dns.name
import requests

from librar.log import log, init as log_init
from librar import misc
from librar import static
from librar.policy import this_policy as policy

CLIENT = None
headers = static.HEADER
headers["X-API-Key"] = os.environ["PDNS_API_KEY"]

PDNS_BASE_URL = "http://127.0.0.1:8081/api/v1/servers/localhost"


def start_up():
    """ Initalisation """
    global CLIENT
    if CLIENT is None:
        CLIENT = requests.Session()
        CLIENT.headers.update(headers)

    catalog_zone = policy.policy("catalog_zone")
    for prefix in ["tlds.", "clients."]:
        try:
            create_zone(prefix + catalog_zone, False, ensure_zone=True, auto_catalog=False)
        except requests.exceptions.ConnectionError:
            raise requests.exceptions.ConnectionError("Failed to connect to PowerDNS")


def find_best_ds(key_data):
    """ pull out the DS record we think is the best one to use """
    for key in key_data:
        if "ds" in key:
            each_ds = {}
            for ds_rr in key["ds"]:
                ds_parts = ds_rr.split()
                each_ds[int(ds_parts[2])] = ds_rr
            for sha_type in [2, 4, 1]:
                if sha_type in each_ds:
                    return each_ds[sha_type]
    return None


def zone_exists(name):
    """ P/DNS will respond differently if the zone exists or not """
    return load_zone_keys(name) is not None


def hash_zone_name(name):
    """ return {name} FQDN as a catalog hash in text """
    if name[-1] != ".":
        name += "."
    return hashlib.sha1(dns.name.from_text(name).to_wire()).hexdigest().lower()


def load_zone(name):
    if name[-1] != ".":
        name += "."
    resp = CLIENT.get(f"{PDNS_BASE_URL}/zones/{name}")
    if resp.status_code < 200 or resp.status_code > 299:
        return None
    return json.loads(resp.content)


def load_zone_keys(name):
    if name[-1] != ".":
        name += "."
    resp = CLIENT.get(f"{PDNS_BASE_URL}/zones/{name}/cryptokeys")
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


def create_zone(name, with_dnssec=False, ensure_zone=False, client_zone=True, auto_catalog=True):
    if name[-1] != ".":
        name += "."

    dns_servers = policy.policy("dns_servers").split(",")
    for idx, ns in enumerate(dns_servers):
        if ns[-1] != ".":
            dns_servers[idx] += "."

    response = run_one_cmd("POST", f"{PDNS_BASE_URL}/zones", {
        "name": name,
        "kind": "Master",
        "masters": [],
        "nameservers": dns_servers,
        "soa_edit_api": "EPOCH"
    })

    if response.status_code >= 400:
        if ensure_zone:
            if auto_catalog:
                add_to_catalog(name, client_zone)
            return True
        log(f"ERROR: Creating '{name}' failed, code={response.status_code} - {response.content}")
        return None

    post_json = []
    if with_dnssec:
        post_json += dnssec_zone_cmds(name)

    now = str(int(time.time()))

    post_json += [{
        "cmd": "PATCH",
        "url": f"{PDNS_BASE_URL}/zones/{name}",
        "data": {
            "rrsets": [{
                "name":
                f"{name}",
                "ttl":
                policy.policy("default_ttl"),
                "type":
                "SOA",
                "changetype":
                "REPLACE",
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
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{name}/notify"
    }]

    run_cmds(post_json)
    if auto_catalog:
        add_to_catalog(name, client_zone)
    return True


def unsign_zone(name):
    if name[-1] != ".":
        name += "."

    keys = load_zone_keys(name)

    post_json = [{
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{name}",
        "data": {
            "nsec3param": ""
        },
    }]

    for key in keys:
        post_json.append({"cmd": "DELETE", "url": f"{PDNS_BASE_URL}/zones/{name}/cryptokeys/{key['id']}"})

    return run_cmds(post_json)


def run_one_cmd(cmd, url, json_data):
    request = requests.Request(cmd, url, json=json_data, headers=headers)
    return CLIENT.send(request.prepare())


def run_cmds(post_json):
    ret = True
    for req in post_json:
        json_data = req["data"] if "data" in req else None
        response = run_one_cmd(req["cmd"], req["url"], json_data)
        if response.status_code < 200 or response.status_code > 299:
            ret = False
            log(f"PDNS-ERROR: {response.content}")
    return ret


def sign_zone(name):
    if name[-1] != ".":
        name += "."
    run_cmds(dnssec_zone_cmds(name))
    return load_zone_keys(name)


def get_catalog(client_zone):
    catalog = policy.policy("catalog_zone")
    return "clients." + catalog if client_zone else "tlds." + catalog


def delete_from_catalog(name, client_zone=True):
    if name[-1] != ".":
        name += "."
    catalog_zone = get_catalog(client_zone)
    zone_hashed = hash_zone_name(name)

    post_json = [{
        "cmd": "PATCH",
        "url": f"{PDNS_BASE_URL}/zones/{catalog_zone}.",
        "data": {
            "rrsets": [{
                "name": f"{zone_hashed}.zones.{catalog_zone}.",
                "ttl": 3600,
                "type": "PTR",
                "changetype": "REPLACE",
                "records": []
            }]
        }
    }, {
        "cmd": "PUT",
        "url": f"{PDNS_BASE_URL}/zones/{catalog_zone}./notify"
    }]

    return run_cmds(post_json)


def add_to_catalog(name, client_zone=True):
    if name[-1] != ".":
        name += "."
    catalog_zone = get_catalog(client_zone)
    zone_hashed = hash_zone_name(name)

    post_json = [{
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
        "url": f"{PDNS_BASE_URL}/zones/{catalog_zone}./notify"
    }]

    return run_cmds(post_json)


def delete_zone(name):
    if name[-1] != ".":
        name += "."

    delete_from_catalog(name)
    return run_cmds([{"cmd": "DELETE", "url": f"{PDNS_BASE_URL}/zones/{name}"}])


def update_rrs(zone, rrs):
    if zone[-1] != ".":
        zone += "."

    if "ttl" not in rrs:
        rrs["ttl"] = policy.policy("default_ttl")

    rr_data = {"changetype": "REPLACE", "records": {}}
    for item in ["name", "ttl", "type"]:
        if item not in rrs:
            return False, f"Missing data item '{item}'"
        rr_data[item] = rrs[item]
    if rr_data["name"][-1] != ".":
        rr_data["name"] += "."

    if "data" in rrs:
        rr_data["records"] = [{"content": val, "disabled": False} for val in rrs["data"]]

    resp = CLIENT.patch(f"{PDNS_BASE_URL}/zones/{zone}", json={"rrsets": [rr_data]}, headers=headers)

    ok = resp.status_code >= 200 and resp.status_code <= 299
    if ok and len(resp.content) == 0:
        return True, True

    try:
        js_content = json.loads(resp.content)
    except Exception:
        return False, "P/DNS Error: Failed to update"

    if ok:
        return True, js_content

    if "error" not in js_content:
        return False, resp

    err_txt = js_content["error"]
    if err_txt.find(":") < 0:
        return False, err_txt

    err_parts = err_txt.split(":")
    if err_txt.find("(try 'pdnsutil check-zone'):") > 0:
        err_txt = err_parts[0] + "&nbsp;<br>&nbsp;" + err_parts[2]
    else:
        err_txt = err_parts[0] + "&nbsp;<br>&nbsp;" + err_parts[1]
    return False, err_txt



def main():
    log_init(with_debug=True)
    start_up()
    # print(create_zone(sys.argv[1],with_dnssec=True,ensure_zone=True))
    print("ZONE>>>>", json.dumps(load_zone(sys.argv[1]), indent=3))
    # print(unsign_zone(name))
    # print("UPDATE>>>",update_rrs(name,{"name":"www.zz","type":"A","data":["1.2.3.4","5.6.5.19"]}))
    # print("KEYS>>>>",load_zone_keys(name))
    # print("CREATE>>>>",json.dumps(create_zone(name, False),indent=3))
    # print("KEYS>>>>", load_zone_keys(name))
    # print("EXISTS>>>>",zone_exists(name))
    # print("DELETE>>>>",json.dumps(delete_zone(name)))
    # print("EXISTS>>>>", zone_exists(name))
    # print("KEYS>>>>",load_zone_keys(name))
    # print("ZONE>>>>", json.dumps(load_zone(sys.argv[1]),indent=3))
    # print(json.dumps(sign_zone("mine"),indent=3))
    # print(json.dumps(load_zone_keys("mine"),indent=3))
    # print(json.dumps(create_zone("mine", True),indent=3))
    # print("cat-add>>>>", json.dumps(add_to_catalog(name)))
    # print("cat-del>>>>", json.dumps(delete_from_catalog(name)))


if __name__ == "__main__":
    main()
