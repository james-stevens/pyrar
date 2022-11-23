#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import sys
import os
import json

import lib.fileloader
from lib.log import log, init as log_init

from inspect import currentframe as czz, getframeinfo as gzz

import MySQLdb as mdb

from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

LOGINS_JSON = os.environ["BASE"] + "/etc/logins.json"

cnx = None
my_login = None

HEXLIB = "0123456789ABCDEF"


def ashex(line):
    ret = ""
    for item in line:
        asc = ord(item)
        ret = ret + HEXLIB[asc >> 4] + HEXLIB[asc & 0xf]
    return ret


def format_data(data):
    """ convert {data} to SQL string """
    if data is None:
        return "NULL"

    if isinstance(data, int):
        return str(int(data))

    if not isinstance(data, str):
        data = str(data)

    return "unhex('" + ashex(data) + "')"


def data_set(data, items=None, joiner=","):
    """ for list of {items} in dictionary {data} create a `item=val` pair """
    the_list = items if items is not None else [item for item in data]
    out = {}
    for item in the_list:
        if item in data:
            out[item] = format_data(data[item])
        fmt = format_data(data[item] if item in data else None)
    return joiner.join([item + "=" + out[item] for item in out])


def sql_run_one(sql):
    if cnx is None:
        log("MySQL not connected",gzz(czz()))
        return False

    try:
        cursor = cnx.cursor()
        cursor.execute(sql)
        lastrowid = cursor.lastrowid
        cnx.commit()
        return True, lastrowid
    except Exception as exc:
        log(exc,gzz(czz()))
        return False, None


def sql_insert(table, data, items=None):
    extra = ""
    chk = items if items is not None else data
    for item in ["when_dt", "amended_dt", "created_dt", "deleted_dt"]:
        if item in chk:
            extra = extra + "," + item + "=now()"
        if item in data:
            del data[item]

    return sql_run_one(f"insert into {table} set " + data_set(data, items) +
                       extra)


def sql_exists(table, data, items=None):
    sql = f"select 1 from {table} where " + data_set(data, items, " and ") + " limit 1"
    ret, __ = run_query(sql)
    return ret and (cnx.affected_rows() > 0)


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


def connect(login):
    """ Connect to MySQL based on ENV vars """

    global cnx
    global my_login

    my_login = login
    logins = lib.fileloader.FileLoader(LOGINS_JSON)
    mysql_json = logins.data()["pyrar"]

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

    cnx = mdb.connect(user=login,
                      passwd=mysql_json[login],
                      unix_socket=sock,
                      host=host,
                      port=port,
                      db=mysql_json["database"],
                      conv=my_conv,
                      charset='utf8mb4',
                      init_command='set names utf8mb4')

def qry_worked(cnx):
    res = cnx.store_result()
    data = res.fetch_row(maxrows=0, how=1)
    return data


def run_query(sql):
    """ run the {sql}, reconnecting to MySQL, if necessary """
    global cnx
    try:
        cnx.query(sql)
        return True, qry_worked(cnx)

    except MySQLdb.OperationalError as exc:
        cnx.close()
        connect(my_login)
        try:
            cnx.query(sql)
            return True, qry_worked(cnx)

        except MySQLdb.OperationalError as exc:
            log(exc,gzz(czz()))
            cnx.close()
            cnx = None
            return False, None
        except MySQLdb.Error as exc:
            log(exc,gzz(czz()))
            return False, None

    except MySQLdb.Error as exc:
        log(exc,gzz(czz()))
        return False, None


def other_tests():
    print(
        data_set({
            "one": 1,
            "two": "22",
            "three": True,
            "four": "this is four",
            "five": None
        }))


if __name__ == "__main__":
    log_init(debug=True)

    connect("webui")

    ret, data = run_query("select * from events limit 3")
    if ret:
        print("ROWS:", cnx.affected_rows())
        print("ROWID:", cnx.insert_id())
        for r in data:
            print(">>>>", json.dumps(r,indent=4))

    print(f">>>> sql exists -> 10452 ->",
          sql_exists("events", {"event_id": 10452}))
    for e in ["james@jrcs.net", "aaa@bbb.com"]:
        print(f">>>> sql exists -> {e} ->",
              sql_exists("users", {"email": e}, ["email"]))

    cnx.close()
