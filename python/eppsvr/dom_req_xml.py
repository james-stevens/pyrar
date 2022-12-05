#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json
import whois_priv


def pad_ds(ds_dt):
    return {"secDNS:" + tag: val for tag, val in ds_dt.items()}


def domain_info(name):
    return {
        "info": {
            "domain:info": {
                "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name": {
                    "@hosts": "all",
                    "#text": name
                }
            }
        }
    }


def domain_request_transfer(name, authcode, years):
    return {
        "transfer": {
            "@op": "request",
            "domain:transfer": {
                "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name": name,
                "domain:period": {
                    "@unit": "y",
                    "#text": str(years)
                },
                "domain:authInfo": {
                    "domain:pw": authcode
                }
            }
        }
    }


def domain_renew(name, years, cur_exp):
    return {
        "renew": {
            "domain:renew": {
                "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name": name,
                "domain:curExpDate": cur_exp,
                "domain:period": {
                    "@unit": "y",
                    "#text": str(years)
                }
            }
        }
    }


def domain_create(name, ns_list, ds_list, years):
    xml = {
        "create": {
            "domain:create": {
                "@xmlns:domain":
                "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name":
                name,
                "domain:period": {
                    "@unit": "y",
                    "#text": str(years)
                },
                "domain:ns": {
                    "domain:hostObj": ns_list
                },
                "domain:registrant":
                whois_priv.WHOIS_PRIVACY_ID,
                "domain:contact": [{
                    "@type": "admin",
                    "#text": whois_priv.WHOIS_PRIVACY_ID
                }, {
                    "@type": "tech",
                    "#text": whois_priv.WHOIS_PRIVACY_ID
                }, {
                    "@type": "billing",
                    "#text": whois_priv.WHOIS_PRIVACY_ID
                }]
            }
        }
    }

    if len(ds_list) > 0:
        xml["extension"] = {
            "secDNS:create": {
                "@xmlns:secDNS": "urn:ietf:params:xml:ns:secDNS-1.1",
                "secDNS:dsData": [pad_ds(ds) for ds in ds_list]
            }
        }

    return xml


def domain_set_authcode(domain, authcode):
    return {
        "update": {
            "domain:update": {
                "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
                "domain:name": domain,
                "domain:chg": {
                    "domain:authInfo": {
                        "domain:pw": authcode if authcode != "" else None
                    }
                }
            }
        }
    }


def domain_update(domain, add_ns, del_ns, add_ds, del_ds):

    update_data = {
        "@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0",
        "domain:name": domain
    }

    if len(add_ns) > 0:
        update_data["domain:add"] = {"domain:ns": {"domain:hostObj": add_ns}}

    if len(del_ns) > 0:
        update_data["domain:rem"] = {"domain:ns": {"domain:hostObj": del_ns}}

    full_xml = {"update": {"domain:update": update_data}}

    if len(add_ds) > 0 or len(del_ds) > 0:
        full_xml["extension"] = {
            "secDNS:update": {
                "@xmlns:secDNS": "urn:ietf:params:xml:ns:secDNS-1.1"
            }
        }
        sec_dns = full_xml["extension"]["secDNS:update"]
        if len(add_ds) > 0:
            sec_dns["secDNS:add"] = {
                "secDNS:dsData": [pad_ds(ds) for ds in add_ds]
            }
        if len(del_ds) > 0:
            sec_dns["secDNS:rem"] = {
                "secDNS:dsData": [pad_ds(ds) for ds in del_ds]
            }

    return full_xml


if __name__ == "__main__":
    print(
        json.dumps(domain_request_transfer("domain.zone", "pass", 1),
                   indent=3))
