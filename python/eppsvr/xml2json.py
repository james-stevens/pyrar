#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

# converts the XML file specified into JSON

import xmltodict
import json
import sys

with open(sys.argv[1]) as fd:
    js = xmltodict.parse(fd.read())

if "epp" in js:
    js = js["epp"]
    if "command" in js:
        js = js["command"]
    if "clTRID" in js:
        del js["clTRID"]

print(json.dumps(js, indent=3))
