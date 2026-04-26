#! /usr/bin/python3

import idna
import json

from librar import misc


def ok_dom(name):
    try:
        n = idna.encode(name)
        return n.decode("utf-8")
    except idna.IDNAError:
        try:
            n = name.encode("idna")
            return n.decode("utf-8")
        except UnicodeError:
            return None
    return None


with open("list3", "r", encoding='UTF-8') as fd:
    lines = fd.readlines()

emojis = []
for line in lines:
    text = line.replace(">", "<").split("<")
    n = ok_dom(text[10])
    if n is not None:
        nd = misc.puny_to_utf8(n, False)
        if nd is not None:
            desc = text[12].strip().lower().replace(":", "")
            emojis.append([nd, desc])

with open("emojis.js", "w", encoding='UTF-8') as fd:
    fd.write("emojis=")
    fd.write(json.dumps(emojis, separators=(',', ':')))

print("Emoji found :",len(emojis))
for x in range(0,5):
    print(x,":",emojis[x])
