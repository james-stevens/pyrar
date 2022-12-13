#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import sys
import argparse

from MySQLdb import _mysql
from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

from lib import fileloader

parser = argparse.ArgumentParser(description='Command line SQL runner')
parser.add_argument("-o", '--output-long', action="store_true")
parser.add_argument("sql", nargs='+')
args = parser.parse_args()


LOGINS_JSON=f"{os.environ['BASE']}/etc/logins.json"
logins = fileloader.load_file_json(LOGINS_JSON)


def convert_string(data):
    if isinstance(data, bytes):
        return data.decode("utf8")
    return data


def convert_datetime(data):
    return data


my_conv = MySQLdb.converters.conversions.copy()
my_conv[FIELD_TYPE.VARCHAR] = convert_string
my_conv[FIELD_TYPE.CHAR] = convert_string
my_conv[FIELD_TYPE.STRING] = convert_string
my_conv[FIELD_TYPE.VAR_STRING] = convert_string
my_conv[FIELD_TYPE.DATETIME] = convert_string
my_conv[FIELD_TYPE.JSON] = convert_string
my_conv[FIELD_TYPE.TINY_BLOB] = convert_string
my_conv[FIELD_TYPE.MEDIUM_BLOB] = convert_string
my_conv[FIELD_TYPE.LONG_BLOB] = convert_string
my_conv[FIELD_TYPE.BLOB] = convert_string

my_conv[FIELD_TYPE.TINY] = int


def mysql_connect(login):
    """ Connect to MySQL based on ENV vars """

    mysql_json = logins["mysql"]
    conn = mysql_json["connect"]
    host = None
    port = None
    sock = ""

    if conn.find("/") >= 0:
        sock = conn
    else:
        host = conn
        port = 3306
        if conn.find(":") >= 0:
            svr = conn.split(":")
            host = svr[0]
            port = int(svr[1])

        return _mysql.connect(user=login,
                             password=mysql_json[login],
                             unix_socket=sock,
                             host=host,
                             port=port,
                             database=mysql_json["database"],
                             conv=my_conv,
                             charset='utf8mb4',
                             init_command='set names utf8mb4')


def max_width(this_row):
    max_len = 0
    for item in this_row:
        this_len = len(item)
        if this_len > max_len:
            max_len = this_len
    return max_len


def verbose_output(this_row):
    wdth = max_width(this_row)
    for item in this_row:
        print(f"{item:{wdth}} = {this_row[item]}")
    print("")


cnx = mysql_connect("raradm")

for sql in args.sql:
    cnx.query(sql)
    res = cnx.store_result()
    FIRST_ROW = sys.stdout.isatty()
    for row in res.fetch_row(maxrows=0, how=1):
        if args.output_long:
            verbose_output(row)
        else:
            if FIRST_ROW:
                print("|".join([str(i) for i in row]))
                FIRST_ROW = False
            print("|".join([str(row[i]) for i in row]))
    cnx.commit()

cnx.close()
