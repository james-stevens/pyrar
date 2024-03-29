#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions to create EPP JSON to be converted into XML """

import json
from backend import whois_priv


def pad_ds(ds_dt):
    """ add `secDNS:` prefix to all DS properties """
    return {"secDNS:" + tag: val for tag, val in ds_dt.items()}


def host_add(hostname, ip_addrs=None):
    """ JSON/XML to add a host """
    host_xml = {
        "create": {
            "host:create": {
                "@xmlns:host": "urn:ietf:params:xml:ns:host-1.0",
                "host:name": hostname,
            }
        }
    }
    if ip_addrs is not None:
        ip_list = ip_addrs if isinstance(ip_addrs, list) else ip_addrs.split(",")
        host_xml["create"]["host:create"]["host:addr"] = []
        host_addr = host_xml["create"]["host:create"]["host:addr"]
        for ip_addr in ip_list:
            ip_ver = "v6" if ip_addr.find(":") >= 0 else "v4"
            host_addr.append({"@ip": ip_ver, "#text": ip_addr})
    return host_xml


def domain_info(name):
    """ JSON/XML to get info on a domain """
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
    """ JSON/XML to request a transfer """
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
    """ JSON/XML to renew a domain """
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
    """ JSON/XML to create a domain """
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
    """ JSON/XML to set the authcode on a domain """
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


def domain_update_flags(domain, add_flags, del_flags):
    """ JSON/XML to update the client flags on a domain """

    update_data = {"@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0", "domain:name": domain}

    if len(add_flags) > 0:
        update_data["domain:add"] = {"domain:status": [{"@s": flag} for flag in add_flags]}

    if len(del_flags) > 0:
        update_data["domain:rem"] = {"domain:status": [{"@s": flag} for flag in del_flags]}

    return {"update": {"domain:update": update_data}}


def domain_update(domain, add_ns, del_ns, add_ds, del_ds):
    """ JSON/XML to update the DS & NS on a domain """

    update_data = {"@xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0", "domain:name": domain}

    if len(add_ns) > 0:
        update_data["domain:add"] = {"domain:ns": {"domain:hostObj": add_ns}}

    if len(del_ns) > 0:
        update_data["domain:rem"] = {"domain:ns": {"domain:hostObj": del_ns}}

    full_xml = {"update": {"domain:update": update_data}}

    if len(add_ds) > 0 or len(del_ds) > 0:
        full_xml["extension"] = {"secDNS:update": {"@xmlns:secDNS": "urn:ietf:params:xml:ns:secDNS-1.1"}}
        sec_dns = full_xml["extension"]["secDNS:update"]
        if len(add_ds) > 0:
            sec_dns["secDNS:add"] = {"secDNS:dsData": [pad_ds(ds) for ds in add_ds]}
        if len(del_ds) > 0:
            sec_dns["secDNS:rem"] = {"secDNS:dsData": [pad_ds(ds) for ds in del_ds]}

    return full_xml


if __name__ == "__main__":
    print(json.dumps(host_add("ns1.dns.com", ["1.2.3.4", "5.6.7.8", "2001:678::1"]), indent=3))
