#! /usr/bin/python3
#################################################################
#    (c) Copyright 2009-2023 JRCS Ltd  - All Rights Reserved    #
#################################################################
""" read the database schema as JSON """

import json
from librar.mysql import sql_server as sql

numbers = {"tinyint", "int", "decimal"}


def sort_elm(fld_elm):
    return fld_elm["Field"]


def make_schema(database):
    schema = {}

    sql.cnx.query("show tables")
    res = sql.cnx.store_result()
    ret = res.fetch_row(maxrows=0, how=1)

    this_db = "Tables_in_" + database

    schema = {table[this_db]: {} for table in ret}

    for table in schema:
        this_tbl = schema[table]
        sql.cnx.query("describe " + table)
        res = sql.cnx.store_result()
        ret = res.fetch_row(maxrows=0, how=1)
        this_tbl["columns"] = {}
        cols = list(ret)
        cols.sort(key=sort_elm)
        for each_col in cols:
            this_tbl["columns"][each_col["Field"]] = {}
            fld_type = each_col["Type"]
            if fld_type.find(" unsigned") >= 0:
                fld_type = fld_type.split()[0]
                this_tbl["columns"][each_col["Field"]]["unsigned"] = True

            pos = fld_type.find("(")
            if pos >= 0:
                fld_sz = fld_type[pos + 1:-1]
                if fld_sz[-2:] == ",0":
                    fld_sz = fld_sz[:-2]
                this_tbl["columns"][each_col["Field"]]["size"] = int(fld_sz)
                fld_type = fld_type[:pos]

            this_tbl["columns"][each_col["Field"]]["type"] = fld_type
            if each_col["Extra"] == "auto_increment":
                this_tbl["columns"][each_col["Field"]]["serial"] = True

            this_tbl["columns"][each_col["Field"]]["null"] = each_col["Null"] == "YES"
            if each_col["Default"] is not None:
                if fld_type in numbers:
                    this_tbl["columns"][each_col["Field"]]["default"] = int(each_col["Default"])
                else:
                    this_tbl["columns"][each_col["Field"]]["default"] = each_col["Default"]

        sql.cnx.query("show index from " + table)
        res = sql.cnx.store_result()
        ret = res.fetch_row(maxrows=0, how=1)
        this_tbl["indexes"] = {}
        for each_idx in ret:
            if each_idx["Key_name"] not in this_tbl["indexes"]:
                this_tbl["indexes"][each_idx["Key_name"]] = {}
                this_tbl["indexes"][each_idx["Key_name"]]["columns"] = []
            this_tbl["indexes"][each_idx["Key_name"]]["columns"].append(each_idx["Column_name"])
            this_tbl["indexes"][each_idx["Key_name"]]["unique"] = each_idx["Non_unique"] == 0

    return schema


def main():
    sql.connect("admin")
    live_schema = make_schema(sql.credentials["database"])
    print(json.dumps(live_schema, indent=3))


if __name__ == "__main__":
    main()
