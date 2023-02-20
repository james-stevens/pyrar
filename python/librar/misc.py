#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions that didn't belong elsewhere """

import inspect
import idna

from librar.policy import this_policy as policy
from librar import mysql as sql
from librar import static


def event_log(other_items, stack_pos=2):
    where = inspect.stack()[stack_pos]
    event_db = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None
    }
    event_db.update(other_items)
    sql.sql_insert("events", event_db)


def ashex(line):
    if isinstance(line, str):
        line = line.encode("utf-8")
    ret = ""
    for asc in line:
        ret += static.HEXLIB[asc >> 4] + static.HEXLIB[asc & 0xf]
    return ret


def puny_to_utf8(name, strict_idna_2008=None):
    if strict_idna_2008 is None:
        strict_idna_2008 = policy.policy("strict_idna2008")
    try:
        idn = idna.decode(name)
        return idn
    except idna.IDNAError:
        if strict_idna_2008:
            return None
        try:
            idn = name.encode("utf-8").decode("idna")
            return idn
        except UnicodeError:
            return None
    return None


def format_currency(number, currency, with_symbol=True):
    num = number
    pfx = currency["symbol"] if with_symbol else ""
    if num < 0:
        pfx += "-"
        num *= -1
    num = str(num)
    places = currency["decimal"]
    if len(num) < (places + 1):
        num = ("000000000000000" + num)[(places + 1) * -1:]
    neg_places = -1 * places
    start = num[:neg_places]
    use_start = ""
    while len(start) > 3:
        use_start += currency["separator"][0] + start[-3:]
        start = start[:-3]
    if len(start) > 0:
        use_start = start + use_start

    return pfx + use_start + currency["separator"][1] + num[neg_places:]


if __name__ == "__main__":
    print(puny_to_utf8("frog.xn--k3h"))
    print(puny_to_utf8("frog.xn--k3hw410f"))
    print(puny_to_utf8("xn--e28h.xn--dp8h"))
    print(puny_to_utf8("xn--strae-oqa.com"))

    print(puny_to_utf8("frog.xn--k3h", True))
    print(puny_to_utf8("frog.xn--k3hw410f", True))
    print(puny_to_utf8("xn--e28h.xn--dp8h", True))
    print(puny_to_utf8("xn--strae-oqa.com", True))
    print(puny_to_utf8("xn--st-rae-oqa.com", True))
