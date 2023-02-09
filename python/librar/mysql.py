#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" Code for interacting with MySQL """

import sys
import json
import datetime
import inspect
from dateutil.relativedelta import relativedelta

from MySQLdb import _mysql
from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

from librar import fileloader
from librar import misc
from librar import static
from librar.log import log, debug, init as log_init

cnx = None
MY_LOGIN = None
MY_PASSWORD = None
MY_DATABASE = None

logins = fileloader.FileLoader(static.LOGINS_FILE)


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


def format_col(column, value):
    """ convert {value} to SQL string """
    if column is not None and value is None and (column in static.NOW_DATE_FIELDS or column[-3:] == "_dt"):
        return f"{column}=now()"

    if value is None:
        return f"{column}=NULL"

    if isinstance(value, int):
        return (column + "=" + str(int(value))) if column else str(int(value))

    if isinstance(value, list):
        return column + " in (" + ",".join(format_col(None, this_val) for this_val in value) + ")"

    if not isinstance(value, str):
        value = str(value)

    ret = "unhex('" + misc.ashex(value.encode("utf8")) + "')"

    if column is not None:
        ret = column + " = " + ret

    return ret


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
    except Exception:
        pass
    connect(MY_LOGIN)


def return_select():
    res = cnx.store_result()
    db_rows = res.fetch_row(maxrows=0, how=1)
    return True, list(db_rows)


def first_not_mysql():
    for context in inspect.stack():
        if context.filename[-9:] != "/mysql.py":
            return context
    return inspect.stack()[1]


def log_sql(sql):
    debug(" SQL " + sql, first_not_mysql())
    # log(" SQL " + sql, first_not_mysql())


def run_sql(sql, func):
    """ run the {sql}, reconnecting to MySQL, if necessary """
    log_sql(sql)
    if cnx is None:
        print(f"Database is not connected '{sql}'")
        log(f"Database is not connected '{sql}'")
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
        log("SQL-ERROR:" + str(this_exc))
        print("SQL-ERROR:" + str(this_exc))
        return None, None


def run_select(sql):
    return run_sql(sql, return_select)


def return_exec():
    lastrowid = cnx.insert_id()
    affected_rows = cnx.affected_rows()
    cnx.store_result()
    cnx.commit()
    return affected_rows, lastrowid


def sql_close():
    cnx.close()


def sql_exec(sql):
    return run_sql(sql, return_exec)


def sql_delete(table, where):
    ok, __ = sql_exec(f"delete from {table} where {data_set(where, ' and ')}")
    return ok is not None


def sql_delete_one(table, where):
    ok, __ = sql_exec(f"delete from {table} where {data_set(where, ' and ')} limit 1")
    return ok is not None


def sql_insert(table, column_vals):
    if table in static.AUTO_CREATED_AMENDED_DT:
        for col in ["amended_dt", "created_dt"]:
            if col not in column_vals:
                column_vals[col] = None
    return sql_exec(f"insert into {table} set " + data_set(column_vals, ","))


def sql_exists(table, where):
    sql = f"select 1 from {table} where " + data_set(where, " and ") + " limit 1"
    ret, __ = run_select(sql)
    return (ret is not None) and (cnx.affected_rows() > 0)


def sql_update_one(table, column_vals, where):
    if table in static.AUTO_CREATED_AMENDED_DT and isinstance(column_vals, dict):
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

    if (reply := run_select(sql))[0] and len(reply[1]) > 0:
        return True, reply[1]

    return False, reply[1]


def sql_select_one(table, where, columns="*"):
    if (reply := sql_select(table, where, columns, 1))[0] and len(reply[1]) > 0:
        return True, reply[1][0]
    return False, reply[1]


def get_pdns_login(login_json):
    if "pdns" not in login_json:
        raise ValueError("ERROR: Could not find P/DNS config in login file")

    pdns_json = login_json["pdns"]
    if not has_data(pdns_json, ["database", "username", "password", "server"]):
        raise ValueError("Missing database or login data for P/DNS")

    return True, pdns_json["server"], pdns_json["username"], pdns_json["password"], pdns_json["database"]


def get_mysql_login(login, login_json):
    if "mysql" not in login_json:
        raise ValueError("ERROR: Could not find MySQL config in login file")

    mysql_json = login_json["mysql"]
    if not has_data(mysql_json, ["database", login, "connect"]):
        raise ValueError(f"Missing server, database or login data for '{login}'")

    find_login = None
    find_passwd = None
    server = mysql_json["connect"]

    if isinstance(mysql_json[login], str):
        find_login = login
        find_passwd = mysql_json[login]
    elif isinstance(mysql_json[login], list) and len(mysql_json[login]) == 2:
        find_login = mysql_json[login][0]
        find_passwd = mysql_json[login][1]
    elif isinstance(mysql_json[login], dict) and has_data(mysql_json[login], ["username", "password"]):
        find_login = mysql_json[login]["username"]
        find_passwd = mysql_json[login]["password"]

    if find_login is None or find_passwd is None:
        raise ValueError(f"Could not find MySQL password for user {login}")

    return True, server, find_login, find_passwd, mysql_json["database"]


def connect(login):
    """ Connect to MySQL based on ENV vars """

    global cnx
    global MY_LOGIN
    global MY_PASSWORD
    global MY_DATABASE

    MY_LOGIN = login
    MY_PASSWORD = None

    if login == "pdns":
        ok, server, MY_LOGIN, MY_PASSWORD, MY_DATABASE = get_pdns_login(logins.data())
    else:
        ok, server, MY_LOGIN, MY_PASSWORD, MY_DATABASE = get_mysql_login(login, logins.data())

    if not ok:
        log(f"ERROR: Could not find credentials for user {login}")
        return False

    host = None
    port = None
    sock = ""

    if server.find("/") >= 0:
        sock = server
    else:
        host = server
        port = 3306
        if server.find(":") >= 0:
            svr = server.split(":")
            host = svr[0]
            port = int(svr[1])

    try:
        cnx = _mysql.connect(user=MY_LOGIN,
                             password=MY_PASSWORD,
                             unix_socket=sock,
                             host=host,
                             port=port,
                             database=MY_DATABASE,
                             conv=my_conv,
                             charset='utf8mb4',
                             init_command='set names utf8mb4')
    except Exception as exc:
        log("Failed to connet to MySQL: " + str(exc))
        cnx = None

    return cnx is not None


def main():
    log_init(with_debug=True)

    connect("pdns")
    print(sql_select("domains", {"1": "1"}))
    sys.exit(0)

    connect("admin")
    print(sql_select_one("domains", {"domain_id": sys.argv[1]}))
    sys.exit(0)

    ret, db_rows = run_select("select * from events limit 3")
    if ret:
        print("ROWS:", cnx.affected_rows())
        print("ROWID:", cnx.insert_id())
        print(">>>> DEBUG", json.dumps(db_rows, indent=4))

    sys.exit(0)

    ret, db_rows = run_select("select * from domains")
    print(">>>> DOMAINS", ret, json.dumps(db_rows, indent=4))

    print(">>>> sql exists -> 10452 ->", sql_exists("events", {"event_id": 10452}))
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


if __name__ == "__main__":
    main()
