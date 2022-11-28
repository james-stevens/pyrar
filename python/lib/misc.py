#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

HEXLIB = "0123456789ABCDEF"


def ashex(line):
    ret = ""
    for item in line:
        asc = ord(item)
        ret = ret + HEXLIB[asc >> 4] + HEXLIB[asc & 0xf]
    return ret
