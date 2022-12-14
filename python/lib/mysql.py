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
NOW_DATE_FIELDS = ["when_dt", "amended_dt", "created_dt", "deleted_dt"]
AUTO_CREATED_AMENDED_DT = ["domains", "epp_jobs", "order_items", "orders", "sales_items", "session_keys", "users"]

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
my_conv[FIELD_TYPE.DECIMAL] = int
my_conv[FIELD_TYPE.NEWDECIMAL] = int


def format_col(item, column_val):
    """ convert {column_val} to SQL string """
    if item in NOW_DATE_FIELDS:
        return f"{item}=now()"

    if column_val is None:
        return f"{item}=NULL"

    if isinstance(column_val, int):
        return item + "=" + str(int(column_val))

    if isinstance(column_val, list):
        return item + " in (" + ",".join(format_col(None, this_val) for this_val in column_val) + ")"

    if not isinstance(column_val, str):
        column_val = str(column_val)

    if item is not None:
        return item + " = unhex('" + misc.ashex(column_val.encode("utf8")) + "')"

    return "unhex('" + misc.ashex(column_val.encode("utf8")) + "')"


def has_data(row, col):
    if isinstance(col, list):
        all_ok = True
        for item in col:
            all_ok = all_ok and has_data(row, item)
        return all_ok
    return (row is not None and col in row and row[col] is not None and row[col] != "")


def now(offset=0):
    now = datetime.datetime.now()
    now += datetime.timedelta(seconds=offset)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def data_set(data, joiner):
    """ create list of `col=val` from dict {data}, joined by {joiner} """
    if data is None:
        return None
    if isinstance(data, str):
        return data
    return joiner.join([format_col(item, data[item]) for item in data])


def reconnect():
    try:
        cnx.close()
    except Exception as exc:
        pass
    connect(my_login)


def return_select():
    res = cnx.store_result()
    db_rows = res.fetch_row(maxrows=0, how=1)
    return True, db_rows


def run_sql(sql, func):
    """ run the {sql}, reconnecting to MySQL, if necessary """
    debug(" SQL " + sql, gzz(czz()))
    if cnx is None:
        print(f"Database is not connected '{sql}'", gzz(czz()))
        log(f"Database is not connected '{sql}'", gzz(czz()))
        return None, None

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
        log("SQL-ERROR:" + str(this_exc), gzz(czz()))
        print("SQL-ERROR:" + str(this_exc), gzz(czz()))
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


def sql_delete_one(table, where):
    ok, __ = sql_exec(f"delete from {table} where {data_set(where, ' and ')} limit 1")
    return ok is not None


def sql_insert(table, column_vals):
    if table in AUTO_CREATED_AMENDED_DT:
        column_vals["amended_dt"] = None
        column_vals["created_dt"] = None
    return sql_exec(f"insert into {table} set " + data_set(column_vals, ","))


def sql_exists(table, where):
    sql = f"select 1 from {table} where " + data_set(where, " and ") + " limit 1"
    ret, __ = run_select(sql)
    return (ret is not None) and (cnx.affected_rows() > 0)


def sql_update_one(table, column_vals, where):
    if table in AUTO_CREATED_AMENDED_DT and isinstance(column_vals, dict):
        column_vals["amended_dt"] = None
    return sql_update(table, column_vals, where, 1)


def sql_update(table, column_vals, where, limit=None):
    update_cols = data_set(column_vals, ",")
    where_clause = data_set(where, " and ")
    sql = f"update {table} set {update_cols} where {where_clause}"
    if limit is not None:
        sql += f" limit {limit}"
    ok, __ = sql_exec(sql)
    return ok is not None


def sql_select(table, where, columns="*", limit=None, order_by=None):
    sql = f"select {columns} from {table} "
    where_clause = data_set(where, " and ")
    if where_clause is not None:
        sql += "where " + where_clause

    if order_by is not None:
        sql += f" order by {order_by}"
    if limit is not None:
        sql += f" limit {limit}"

    ok, db_rows = run_select(sql)

    if not ok:
        return False, None

    return True, db_rows


def sql_select_one(table, where, columns="*"):
    ok, db_rows = sql_select(table, where, columns, 1)
    if ok:
        if len(db_rows) > 0:
            return True, db_rows[0]
        else:
            return True, {}
    return False, None


def connect(login):
    """ Connect to MySQL based on ENV vars """

    global cnx
    global my_login

    logins.check_for_new()
    my_login = login
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

    try:
        cnx = _mysql.connect(user=login,
                             password=mysql_json[login],
                             unix_socket=sock,
                             host=host,
                             port=port,
                             database=mysql_json["database"],
                             conv=my_conv,
                             charset='utf8mb4',
                             init_command='set names utf8mb4')
    except Exception as exc:
        log("Failed to connet to MySQL: " + str(exc), gzz(czz()))
        cnx = None


if __name__ == "__main__":
    log_init(with_debug=True)

    print(format_col("name", ["one", "two", "three"]))
    sys.exit(0)

    connect("webui")

    ret, db_rows = run_select("select * from events limit 3")
    if ret:
        print("ROWS:", cnx.affected_rows())
        print("ROWID:", cnx.insert_id())
        print(">>>> DEBUG", json.dumps(db_rows, indent=4))

    ret, db_rows = run_select("select * from domains")
    print(">>>> DOMAINS", ret, json.dumps(db_rows, indent=4))

    print(f">>>> sql exists -> 10452 ->", sql_exists("events", {"event_id": 10452}))
    for e in ["james@jrcs.net", "aaa@bbb.com"]:
        print(f">>>> sql exists -> {e} ->", sql_exists("users", {"email": e}))

    cnx.close()

    ret, db_rows = sql_select_one("Xevents", {"event_id": 10452})
    print(">>SELECT>>>", ret, json.dumps(db_rows, indent=4))

    ret, db_rows = sql_select_one("zones", {"zone": "chug"})
    print(">>SELECT>>>", ret, json.dumps(db_rows, indent=4))
    ret, db_rows = sql_select_one("zones", {"zone": "chug-XXX"})
    print(">>SELECT>>>", ret, json.dumps(db_rows, indent=4))

    ret = sql_update_one("session_keys", {"amended_dt": None}, {"user_id": 10465})
    print(">>UPDATE>>>", ret)

    cnx.close()
