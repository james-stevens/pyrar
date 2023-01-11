#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions & XML to check whois-privacy contact record exists """

import json

from librar import misc
from backend import xmlapi

WHOIS_PRIVACY_ID = "whoisPrivacy"

whois_privacy_info = {
    "info": {
        "contact:info": {
            "@xmlns:contact": "urn:ietf:params:xml:ns:contact-1.0",
            "contact:id": WHOIS_PRIVACY_ID
        }
    }
}

whois_privacy_contact = {
    "create": {
        "contact:create": {
            "@xmlns:contact": "urn:ietf:params:xml:ns:contact-1.0",
            "@xsi:schemaLocation": "urn:ietf:params:xml:ns:contact-1.0 contact-1.0.xsd",
            "contact:id": WHOIS_PRIVACY_ID,
            "contact:postalInfo": {
                "@type": "int",
                "contact:name": "Whois Privacy",
                "contact:org": "WhoisPrivacy",
                "contact:addr": {
                    "contact:street": "Whois Privacy",
                    "contact:city": "Whois Privacy",
                    "contact:sp": "Whois Privacy",
                    "contact:pc": "Whois Privacy",
                    "contact:cc": "US"
                }
            },
            "contact:voice": "+123.1234567890",
            "contact:email": "null@example.com",
            "contact:authInfo": {
                "contact:pw": "*"
            }
        }
    }
}


def check_privacy_exists(client, url):
    """ check EPP rest/api for {client} at {url} has whois-privacy contact """
    resp = client.post(url, json=whois_privacy_info, headers=misc.HEADER)
    if resp.status_code < 200 or resp.status_code > 299:
        return False

    reply = json.loads(resp.content)
    if xmlapi.xmlcode(reply) == 1000:
        return True

    resp = client.post(url, json=whois_privacy_contact, headers=misc.HEADER)
    if resp.status_code < 200 or resp.status_code > 299:
        return False

    reply = json.loads(resp.content)
    if xmlapi.xmlcode(reply) == 1000:
        return True

    return False
