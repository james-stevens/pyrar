#! /usr/bin/python3

import sys
import json
import collections


class flatDict:
    def __init__(self,js):
        self.flat = {}
        self.dispatch([],js)

    def dispatch(self,pfx,js):
        if isinstance(js,dict) or isinstance(js,collections.OrderedDict):
            for itm in js:
                self.dispatch(pfx+[itm],js[itm])
        elif isinstance(js,list):
            i = 0
            for itm in js:
                self.dispatch(pfx + ["[{0:02x}]".format(i:=i+1)],itm)
        else:
            s = ".".join(pfx)
            self.flat[s] = js


del(sys.argv[0])
for file in sys.argv:
    with open(file,"r") as fd:
        inpjs = json.load(fd)

    flat = flatDict(inpjs).flat
    for item in flat:
        print(f"{item}={flat[item]}")
