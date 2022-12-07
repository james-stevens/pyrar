#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import sys
import os
import json
import datetime

import lib.fileloader
from lib import misc
from lib.log import log, debug, init as log_init

from inspect import currentframe as czz, getframeinfo as gzz

from MySQLdb import _mysql
from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

LOGINS_JSON = os.environ["BASE"] + "/etc/logins.json"
DATE_FIELDS = ["when_dt", "amended_dt", "created_dt", "deleted_dt"]

cnx = None
my_login = None

logins = lib.fileloader.FileLoader(LOGINS_JSON)


def convert_string(data):
    if isinstance(data, bytes):
        return data.decode("utf8")
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


def format_data(item, data):
    """ convert {data} to SQL string """
    if item in DATE_FIELDS:
        return "now()"

    if data is None:
        return "NULL"

    if isinstance(data, int):
        return str(int(data))

    if not isinstance(data, str):
        data = str(data)

    return "unhex('" + misc.ashex(data) + "')"


def has_data(row, col):
    return (row is not None and col in row and row[col] is not None and row[col] != "")


def now(offset=0):
    now = datetime.datetime.now()
    now += datetime.timedelta(seconds=offset)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def data_set(data, joiner):
    """ create list of `col=val` from dict {data}, joined by {joiner} """
    if isinstance(data, str):
        return data
    return joiner.join(
        [item + "=" + format_data(item, data[item]) for item in data])


def reconnect():
    try:
        cnx.close()
    except Exception as exc:
        pass
    connect(my_login)


def return_select():
    res = cnx.store_result()
    data = res.fetch_row(maxrows=0, how=1)
    return True, data


def run_sql(sql, func):
    """ run the {sql}, reconnecting to MySQL, if necessary """
    debug(" SQL " + sql, gzz(czz()))
    try:
        cnx.query(sql)
        return func()

    except Exception as exc:
        this_exc = exc
        if exc.args[0] == 2006:
            reconnect()
            try:
                cnx.query(sql)
                return func()
            except Exception as exc:
                this_exc = exc
                pass
        log("ERROR:" + str(this_exc), gzz(czz()))
        return None, None


def run_select(sql):
    return run_sql(sql, return_select)


def return_exec():
    lastrowid = cnx.insert_id()
    affected_rows = cnx.affected_rows()
    cnx.store_result()
    cnx.commit()
    return affected_rows, lastrowid


def sql_exec(sql):
    return run_sql(sql, return_exec)


def sql_delete_one(table, data):
    return sql_exec(f"delete from {table} where " + data_set(data, " and ") +
                    " limit 1")


def sql_insert(table, data):
    return sql_exec(f"insert into {table} set " + data_set(data, ","))


def sql_exists(table, data):
    sql = f"select 1 from {table} where " + data_set(data,
                                                     " and ") + " limit 1"
    ret, __ = run_select(sql)
    return (ret is not None) and (cnx.affected_rows() > 0)


def sql_update_one(table, data, where):
    ret, val = sql_update(table, data, where, 1)
    return (ret in [0,1]), val


def sql_update(table, data, where, limit=None):
    sql = f"update {table} set " + data_set(data, ",") + " where " + data_set(
        where, " and ")
    if limit is not None:
        sql += f" limit {limit}"
    return sql_exec(sql)


def sql_select(table, where, columns="*", limit=None, order_by=None):
    sql = f"select {columns} from {table} where " + data_set(where, " and ")
    if order_by is not None:
        sql += f" order by {order_by}"
    if limit is not None:
        sql += f" limit {limit}"

    ret, data = run_select(sql)

    if not ret:
        return None, None

    num_rows = cnx.affected_rows()
    return num_rows, data


def sql_select_one(table, where, columns="*"):
    num, data = sql_select(table, where, columns, 1)
    return num, data[0] if num == 1 else None


def connect(login):
    """ Connect to MySQL based on ENV vars """

    global cnx
    global my_login

    logins.check_for_new()
    my_login = login
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

    cnx = _mysql.connect(user=login,
                         password=mysql_json[login],
                         unix_socket=sock,
                         host=host,
                         port=port,
                         database=mysql_json["database"],
                         conv=my_conv,
                         charset='utf8mb4',
                         init_command='set names utf8mb4')


if __name__ == "__main__":
    log_init(debug=True)
    connect("webui")

    ret, data = run_select("select * from events limit 3")
    if ret:
        print("ROWS:", cnx.affected_rows())
        print("ROWID:", cnx.insert_id())
        print(">>>>", json.dumps(data, indent=4))

    ret, data = run_select("select * from domains")
    print(">>>> DOMAINS", ret, json.dumps(data, indent=4))

    print(f">>>> sql exists -> 10452 ->",
          sql_exists("events", {"event_id": 10452}))
    for e in ["james@jrcs.net", "aaa@bbb.com"]:
        print(f">>>> sql exists -> {e} ->", sql_exists("users", {"email": e}))

    cnx.close()

    ret, data = sql_select_one("Xevents", {"event_id": 10452})
    print(">>SELECT>>>", ret, json.dumps(data, indent=4))

    ret, data = sql_select_one("events", {"event_id": 10471})
    print(">>SELECT>>>", ret, json.dumps(data, indent=4))

    ret, data = sql_update_one("session_keys", {"amended_dt": None},
                               {"user_id": 10465})
    print(">>UPDATE>>>", ret, data)

    cnx.close()
