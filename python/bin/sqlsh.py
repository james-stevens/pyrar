#! /usr/bin/python3

import sys
import os

from MySQLdb import _mysql
from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

with_verbose = True

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
my_conv[FIELD_TYPE.DATETIME] = convert_datetime


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


def max_width(row):
    max_len = 0
    for r in row:
        l = len(r)
        if l > max_len:
            max_len = l
    return max_len


def verbose_output(row):
    wdth = max_width(row)
    for r in row:
        print(f"{r:{wdth}} = {row[r]}")
    print("")


cnx = mysql_connect()

del sys.argv[0]
for sql in sys.argv:
    cnx.query(sql)
    res = cnx.store_result()
    first_row = True
    for row in res.fetch_row(maxrows=0, how=1):
        if with_verbose:
            verbose_output(row)
        else:
            if first_row:
                print("|".join([str(i) for i in row]))
                first_row = False
            print("|".join([str(row[i]) for i in row]))
    cnx.commit()

cnx.close()
