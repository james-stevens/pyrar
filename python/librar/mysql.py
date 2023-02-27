#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" Code for interacting with MySQL """

import sys
import json
import inspect

from MySQLdb import _mysql
from MySQLdb.constants import FIELD_TYPE
import MySQLdb.converters

from librar import fileloader
from librar import misc
from librar import static
from librar.log import log, debug, init as log_init

ALL_CREDENTIALS = ["database", "username", "password", "server"]


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


def event_log(other_items, stack_pos=2):
    where = inspect.stack()[stack_pos]
    event_db = {
        "program": where.filename.split("/")[-1].split(".")[0],
        "function": where.function,
        "line_num": where.lineno,
        "when_dt": None
    }
    event_db.update(other_items)
    sql_server.sql_insert("events", event_db)


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


def data_set(data, joiner):
    """ create list of `col=val` from dict {data}, joined by {joiner} """
    if data is None:
        return None
    if isinstance(data, str):
        return data
    return joiner.join([format_col(item, data[item]) for item in data])


def first_not_mysql():
    for context in inspect.stack():
        if context.filename[-9:] != "/mysql.py":
            return context
    return inspect.stack()[1]


def log_sql(sql):
    debug(" SQL " + sql, first_not_mysql())
    # log(f" SQL: {sql}")


class MariaDB:
    def __init__(self):
        self.which_connector = None
        self.credentials = None
        self.tcp_cnx = None
        self.logins = fileloader.FileLoader(static.LOGINS_FILE)

    def close(self):
        self.tcp_cnx.close()

    def reconnect(self):
        try:
            self.close()
        except Exception:
            pass
        return self.actually_connect()

    def return_select(self):
        res = self.tcp_cnx.store_result()
        db_rows = res.fetch_row(maxrows=0, how=1)
        return True, list(db_rows)

    def sql_run(self, sql, func):
        """ run the {sql}, reconnecting to MySQL, if necessary """
        log_sql(sql)
        if self.tcp_cnx is None:
            print(f"Database is not connected '{sql}'")
            log(f"Database is not connected '{sql}'")
            return None, None

        sql_server.tcp_cnx.ping(True)
        try:
            self.tcp_cnx.query(sql)
            return func()

        except Exception as exc:
            this_exc = exc
            if exc.args[0] == 2006:
                self.reconnect()
                try:
                    self.tcp_cnx.query(sql)
                    return func()
                except Exception as exc:
                    this_exc = exc
            log(f"SQL: {sql}")
            log("SQL-ERROR:" + str(this_exc))
            print("SQL-ERROR:" + str(this_exc))
            return False, this_exc.args[1]

    def run_select(self, sql):
        return self.sql_run(sql, self.return_select)

    def return_exec(self):
        lastrowid = self.tcp_cnx.insert_id()
        affected_rows = self.tcp_cnx.affected_rows()
        self.tcp_cnx.store_result()
        self.tcp_cnx.commit()
        return affected_rows, lastrowid

    def sql_close(self):
        self.tcp_cnx.close()

    def sql_exec(self, sql):
        return self.sql_run(sql, self.return_exec)

    def sql_delete(self, table, where):
        ok, __ = self.sql_exec(f"delete from {table} where {data_set(where, ' and ')}")
        return ok is not None

    def sql_delete_one(self, table, where):
        ok, __ = self.sql_exec(f"delete from {table} where {data_set(where, ' and ')} limit 1")
        return ok is not None

    def sql_insert(self, table, column_vals, ignore=False):
        if table in static.AUTO_CREATED_AMENDED_DT:
            for col in ["amended_dt", "created_dt"]:
                if col not in column_vals:
                    column_vals[col] = None
        with_ignore = "ignore" if ignore else ""
        return self.sql_exec(f"insert {with_ignore} into {table} set " + data_set(column_vals, ","))

    def sql_exists(self, table, where):
        sql = f"select 1 from {table} where " + data_set(where, " and ") + " limit 1"
        ret, __ = self.run_select(sql)
        return (ret is not None) and (self.tcp_cnx.affected_rows() > 0)

    def sql_update_one(self, table, column_vals, where):
        if table in static.AUTO_CREATED_AMENDED_DT and isinstance(column_vals, dict):
            column_vals["amended_dt"] = None
        return self.sql_update(table, column_vals, where, 1)

    def sql_update(self, table, column_vals, where, limit=None):
        update_cols = data_set(column_vals, ",")
        where_clause = data_set(where, " and ")
        sql = f"update {table} set {update_cols} where {where_clause}"
        if limit is not None:
            sql += f" limit {limit}"
        ok, __ = self.sql_exec(sql)
        return ok is not None

    def sql_select(self, table, where, columns="*", limit=None, order_by=None):
        sql = f"select {columns} from {table} "
        where_clause = data_set(where, " and ")
        if where_clause is not None:
            sql += "where " + where_clause

        if order_by is not None:
            sql += f" order by {order_by}"
        if limit is not None:
            sql += f" limit {limit}"

        if (reply := self.run_select(sql))[0] and len(reply[1]) > 0:
            return True, reply[1]

        return False, reply[1]

    def sql_select_one(self, table, where, columns="*"):
        if (reply := self.sql_select(table, where, columns, 1))[0] and len(reply[1]) > 0:
            return True, reply[1][0]
        return False, reply[1]

    def get_pdns_login(self):
        logins_data = self.logins.data()
        if "pdns" not in logins_data:
            raise ValueError("ERROR: Could not find P/DNS config in login file")

        pdns_json = logins_data["pdns"]
        if not misc.has_data(pdns_json, ALL_CREDENTIALS):
            raise ValueError("Missing database or login data for P/DNS")

        self.credentials = {cred: pdns_json[cred] for cred in ALL_CREDENTIALS}
        return True

    def get_mysql_login(self):
        logins_data = self.logins.data()
        if "mysql" not in logins_data:
            raise ValueError("ERROR: Could not find MySQL config in login file")

        mysql_json = logins_data["mysql"]
        if not misc.has_data(mysql_json, ["database", self.which_connector, "connect"]):
            raise ValueError(f"Missing server, database or login data for '{self.which_connector}'")

        self.credentials = {cred: None for cred in ALL_CREDENTIALS}
        self.credentials["server"] = mysql_json["connect"]

        if isinstance(mysql_json[self.which_connector], str):
            self.credentials["username"] = self.which_connector
            self.credentials["password"] = mysql_json[self.which_connector]
        elif isinstance(mysql_json[self.which_connector], list) and len(mysql_json[self.which_connector]) == 2:
            self.credentials["username"] = mysql_json[self.which_connector][0]
            self.credentials["password"] = mysql_json[self.which_connector][1]
        elif isinstance(mysql_json[self.which_connector], dict) and misc.has_data(mysql_json[self.which_connector],
                                                                                  ["username", "password"]):
            self.credentials["username"] = mysql_json[self.which_connector]["username"]
            self.credentials["password"] = mysql_json[self.which_connector]["password"]

        self.credentials["database"] = mysql_json["database"]

        if not misc.has_data(self.credentials, ALL_CREDENTIALS):
            raise ValueError(f"Could not find MySQL password for service '{self.which_connector}'")

        return True

    def connect(self, login=None):
        """ Connect to MySQL based on ENV vars """

        if login:
            self.which_connector = login
        else:
            if self.which_connector is None:
                raise ValueError("Reconnect, but no initial login set")

        return self.actually_connect()

    def actually_connect(self):

        ok = self.get_pdns_login() if self.which_connector == "pdns" else self.get_mysql_login()
        if not ok:
            raise ValueError(f"ERROR: Could not find credentials for user {self.which_connector}")

        host = port = None
        sock = ""

        if self.credentials["server"].find("/") >= 0:
            sock = self.credentials["server"]
        else:
            host = self.credentials["server"]
            port = 3306
            if self.credentials["server"].find(":") >= 0:
                svr = self.credentials["server"].split(":")
                host = svr[0]
                port = int(svr[1])

        try:
            new_cnx = _mysql.connect(user=self.credentials["username"],
                                     password=self.credentials["password"],
                                     unix_socket=sock,
                                     host=host,
                                     port=port,
                                     database=self.credentials["database"],
                                     conv=my_conv,
                                     charset='utf8mb4',
                                     init_command='set names utf8mb4')
            self.tcp_cnx = new_cnx
        except Exception as exc:
            log("Failed to connet to MySQL: " + str(exc))
            self.tcp_cnx = None

        return self.tcp_cnx is not None


sql_server = MariaDB()


def main():
    log_init(with_debug=True)
    # sql_server.connect("engine")
    # sql_server.tcp_cnx.ping(True)
    # sys.exit(0)

    sql_server.connect("pdns")
    print(sql_server.sql_select("domains", {"1": "1"}))
    sys.exit(0)

    sql_server.connect("admin")
    print(sql_server.sql_select_one("domains", {"domain_id": sys.argv[1]}))
    sys.exit(0)

    ret, db_rows = sql_server.run_select("select * from events limit 3")
    if ret:
        print("ROWS:", sql_server.tcp_cnx.affected_rows())
        print("ROWID:", sql_server.tcp_cnx.insert_id())
        print(">>>> DEBUG", json.dumps(db_rows, indent=4))

    sys.exit(0)

    ret, db_rows = sql_server.run_select("select * from domains")
    print(">>>> DOMAINS", ret, json.dumps(db_rows, indent=4))

    print(">>>> sql exists -> 10452 ->", sql_server.sql_exists("events", {"event_id": 10452}))
    for e in ["james@jrcs.net", "aaa@bbb.com"]:
        print(f">>>> sql exists -> {e} ->", sql_server.sql_exists("users", {"email": e}))

    sql_server.close()

    ret, db_rows = sql_server.sql_select_one("Xevents", {"event_id": 10452})
    print(">>SELECT>>>", ret, json.dumps(db_rows, indent=4))

    ret, db_rows = sql_server.sql_select_one("zones", {"zone": "chug"})
    print(">>SELECT>>>", ret, json.dumps(db_rows, indent=4))
    ret, db_rows = sql_server.sql_select_one("zones", {"zone": "chug-XXX"})
    print(">>SELECT>>>", ret, json.dumps(db_rows, indent=4))

    ret = sql_server.sql_update_one("session_keys", {"amended_dt": None}, {"user_id": 10465})
    print(">>UPDATE>>>", ret)

    sql_server.close()


if __name__ == "__main__":
    main()
