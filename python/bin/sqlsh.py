#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
import argparse

from MySQLdb import _mysql
from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

parser = argparse.ArgumentParser(description='Command line SQL runner')
parser.add_argument("-o", '--output-long', action="store_true")
parser.add_argument("sql",nargs='+')
args = parser.parse_args()


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


def mysql_connect():
    """ Connect to MySQL based on ENV vars """
    sock = "/tmp/mysql.sock"
    host = None
    port = None
    if "MYSQL_CONNECT" in os.environ:
        conn = os.environ["MYSQL_CONNECT"]
        if conn.find("/") >= 0:
            sock = conn
        else:
            host = conn
            port = 3306
            if conn.find(":") >= 0:
                svr = conn.split(":")
                host = svr[0]
                port = int(svr[1])

    # pylint: disable=c-extension-no-member
    return _mysql.connect(
        user=os.environ["MYSQL_USERNAME"],
        password=os.environ["MYSQL_PASSWORD"],
        unix_socket=sock,
        host=host,
        port=port,
        database=os.environ["MYSQL_DATABASE"],
        conv=my_conv,
        charset='utf8mb4',
        init_command='set names utf8mb4',
    )


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


cnx = mysql_connect()

print(">>>>>",args.sql)
for sql in args.sql:
    print(">>>>",sql)
    cnx.query(sql)
    res = cnx.store_result()
    FIRST_ROW = True  # pylint incorrectly thinks this is a Constant
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
