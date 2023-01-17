#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" script for running SQL in shell """

import os
import sys
import argparse

from librar import mysql as sql
from librar import fileloader
from librar import static_data

parser = argparse.ArgumentParser(description='Command line SQL runner')
parser.add_argument("-o", '--output-long', action="store_true")
parser.add_argument("sql", nargs='+')
args = parser.parse_args()

logins = fileloader.load_file_json(static_data.LOGINS_FILE)


def max_width(this_row):
    """ return width of widest column name """
    max_len = 0
    for item in this_row:
        this_len = len(item)
        if this_len > max_len:
            max_len = this_len
    return max_len


def verbose_output(this_row):
    """ output one column per line """
    wdth = max_width(this_row)
    for item in this_row:
        print(f"{item:{wdth}} = {this_row[item]}")
    print("")


sql.connect("admin")

for query in args.sql:
    ok, reply = sql.run_select(query)
    FIRST_ROW = sys.stdout.isatty()
    for row in reply:
        if args.output_long:
            verbose_output(row)
        else:
            if FIRST_ROW:
                print("|".join([str(i) for i in row]))
                FIRST_ROW = False
            print("|".join([str(row[i]) for i in row]))

sql.sql_close()
