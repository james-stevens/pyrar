#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" display JSON files as flat text for processing in shell scripts """

import sys
import json
import collections


def flatten(in_js):
    out_flat = {}
    do_flatten([], in_js, out_flat)
    return out_flat


def do_flatten(pfx, inp_js, out_flat):
    if isinstance(inp_js, (dict, collections.OrderedDict)):
        for itm in inp_js:
            do_flatten(pfx + [itm], inp_js[itm], out_flat)
    elif isinstance(inp_js, list):
        idx = 0
        for itm in inp_js:
            do_flatten(pfx + [f"[{(idx := idx + 1):02x}]"], itm, out_flat)
    else:
        out_flat[".".join(pfx)] = inp_js


if __name__ == "__main__":
    for file in sys.argv[1:]:
        with open(file, "r", encoding='UTF-8') as fd:
            read_js = json.load(fd)
            print(json.dumps(flatten(read_js), indent=3))
