#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import sys
import os
import json

import lib.fileloader
import lib.log

import MySQLdb as mdb

from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

LOGINS_JSON = os.environ["BASE"] + "/etc/logins.json"

cnx = None
my_login = None


def format_data(data):
    """ convert {data} to SQL string """
    if data is None:
        return "NULL"

    if isinstance(data, bool):
        return "1" if data else "0"

    if isinstance(data, int):
        return str(data)

    if not isinstance(data, str):
        data = str(data)

    return "unhex('" + "".join([hex(ord(a))[2:] for a in data]) + "')"


def data_set(data,items=None,joiner=","):
    """ for list of {items} in dictionary {data} create a `item=val` pair """
    the_list = items if items is not None else [ item for item in data]

    out = { item:format_data(data[item] if item in data else None) for item in the_list }

    if "amended_dt" in items:
        out["amended_dt"] = "now()"
    if "created_dt" in items:
        out["created_dt"] = "now()"

    return joiner.join([item + "=" + out[item] for item in out])


def sql_run_one(sql):
    try:
        cursor = cnx.cursor()
        cursor.execute(sql)
        cnx.commit()
        return True
    except Exception as exc:
        return False


def sql_insert(table, data, items = None):
    return sql_run_one(f"insert into {table} set " + data_set(data,items))


def sql_exists(table, data, items = None):
    sql = f"select 1 from {table} where " + data_set(data,items," and ")
    if (run_query(sql)):
        res = cnx.store_result()
        rows = [r for r in res.fetch_row(maxrows=0, how=1)]
        return (len(rows) > 0)
    return False


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
    mysql_json = logins.data()["mysql"]

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

    cnx = mdb.connect(
        user=login,
        passwd=mysql_json[login],
        unix_socket=sock,
        host=host,
        port=port,
        db=mysql_json["database"],
        conv=my_conv,
        charset='utf8mb4',
        init_command='set names utf8mb4'
    )


def run_query(sql):
    """ run the {sql}, reconnecting to MySQL, if necessary """
    global cnx
    try:
        cnx.query(sql)
        return True

    except MySQLdb.OperationalError as exc:
        cnx.close()
        connect(my_login)
        try:
            cnx.query(sql)
            return True

        except MySQLdb.OperationalError as exc:
            print(">>>>>",exc)
            lib.log.log(exc)
            cnx.close()
            cnx = None
            return False
        except MySQLdb.Error as exc:
            print(">>>>>",exc)
            lib.log.log(exc)
            return False

    except MySQLdb.Error as exc:
        print(">>>>>",exc)
        lib.log.log(exc)
        return False




if __name__ == "__main__":
    print(
        data_set({
            "one": 1,
            "two": "22",
            "three": True,
            "four": "this is four",
            "five": None
        }))

    lib.log.debug = True

    connect("webui")

    if (run_query("show tables")):
        print("ROWS:",cnx.affected_rows())
        print("ROWID:",cnx.insert_id())
        res = cnx.store_result()
        for r in res.fetch_row(maxrows=0, how=1):
            print(">>>>",r)

    for e in ["james@jrcs.net","aaa@bbb.com"]:
        print(f">>>> sql exists -> {e} ->",sql_exists("users",{"email":e},["email"]))

    cnx.close()

