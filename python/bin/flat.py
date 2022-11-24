#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" display JSON files as flat text For processing in shall scripts """
import sys
import json
import collections


def flatten(pfx, inp_js):
    """ recursive function to display {inp_js} JSON in a flat format """
    if isinstance(inp_js, (dict, collections.OrderedDict)):
        for itm in inp_js:
            flatten(pfx + [itm], inp_js[itm])
    elif isinstance(inp_js, list):
        i = 0
        for itm in inp_js:
            flatten(pfx + [f"[{(i := i + 1):02x}]"], itm)
    else:
        print(f"{'.'.join(pfx)}={inp_js}")


del sys.argv[0]
for file in sys.argv:
    with open(file, "r", encoding='UTF-8') as fd:
        read_js = json.load(fd)
        flatten([], read_js)
