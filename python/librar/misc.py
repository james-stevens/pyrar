#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions that didn't belong elsewhere """

import os
import datetime
import sys
import idna
from dateutil.relativedelta import relativedelta

from librar.policy import this_policy as policy
from librar import static


HEXLIB = "0123456789ABCDEF"


def ashex(line):
    if isinstance(line, int):
        out_hex = ""
        while line > 0:
            out_hex = HEXLIB[line & 0xf] + out_hex
            line = line >> 4
        return out_hex if len(out_hex) > 0 else "0"
    if isinstance(line, str):
        line = line.encode("utf-8")
    ret = ""
    for asc in line:
        ret += HEXLIB[asc >> 4] + HEXLIB[asc & 0xf]
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


def amt_from_float(amt, currency=None):
    if currency is None:
        currency = policy.policy("currency")
    amt = float(amt)
    amt *= static.POW10[currency["decimal"]]
    return int(round(float(amt), 0))


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


def has_data(row, col):
    if isinstance(col, list):
        all_ok = True
        for item in col:
            all_ok = all_ok and has_data(row, item)
        return all_ok
    return row is not None and len(row) > 0 and col in row and row[col] is not None and row[col] != ""


def now(offset=0):
    time_now = datetime.datetime.now()
    time_now += datetime.timedelta(seconds=offset)
    return time_now.strftime("%Y-%m-%d %H:%M:%S")


def date_add(mysql_time, days=0, hours=0, years=0):
    time_now = datetime.datetime.strptime(mysql_time, "%Y-%m-%d %H:%M:%S")
    time_now += relativedelta(days=days, hours=hours, years=years)
    return time_now.strftime("%Y-%m-%d %H:%M:%S")


def make_year_month_day_dir(start_dir):
    for date_part in datetime.datetime.now().strftime("%Y,%m,%d").split(","):
        start_dir = os.path.join(start_dir, date_part)
        if not os.path.isdir(start_dir):
            os.mkdir(start_dir)
            os.chmod(start_dir, 0o777)
    return start_dir


if __name__ == "__main__":
    print(make_year_month_day_dir("/tmp/dt"))
    #print(amt_from_float(sys.argv[1]))
    #print(ashex(int(sys.argv[1])))

    # print(puny_to_utf8("frog.xn--k3h"))
    # print(puny_to_utf8("frog.xn--k3hw410f"))
    # print(puny_to_utf8("xn--e28h.xn--dp8h"))
    # print(puny_to_utf8("xn--strae-oqa.com"))

    # print(puny_to_utf8("frog.xn--k3h", True))
    # print(puny_to_utf8("frog.xn--k3hw410f", True))
    # print(puny_to_utf8("xn--e28h.xn--dp8h", True))
    # print(puny_to_utf8("xn--strae-oqa.com", True))
    # print(puny_to_utf8("xn--st-rae-oqa.com", True))
    sys.exit(0)
