#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" update this schema to match etc/schema """

import json
import os
import sys
import argparse
import filecmp

from librar import mysql
from librar.mysql import sql_server as sql
from librar.policy import this_policy as policy

SCHEMA_FILE = f"{os.environ['BASE']}/etc/schema.json"
SCHEMA_PDNS = f"{os.environ['BASE']}/etc/pdns.json"


def property_same(name, col1, col2):
    if name not in col1 and name not in col2:
        return True
    if name in col1 and name not in col2:
        return False
    if name not in col1 and name in col2:
        return False
    if col1[name] != col2[name]:
        return False
    return True


def type_change(col1, col2):
    """ check to see if the column type or size has changed """
    if col1["type"] != col2["type"]:
        return True
    return any(not property_same(property, col1, col2) for property in ["size", "null", "default"])


parser = argparse.ArgumentParser(description='EPP Jobs Runner')
parser.add_argument("-C", '--recreate', action="store_true")
parser.add_argument("-D", '--debug', action="store_true")
parser.add_argument("-l", '--login', default="admin")
args = parser.parse_args()

sql.connect(args.login)
sql.make_schema()

filename = SCHEMA_FILE
if args.login == "pdns":
    filename = SCHEMA_PDNS

if args.recreate:
    new_file = filename + ".new"
    if os.path.isfile(new_file):
        os.remove(new_file)

    with open(new_file, "w", encoding="UTF-8") as fd:
        fd.write(json.dumps(sql.schema, indent=3))

    if os.path.isfile(filename) and filecmp.cmp(new_file, filename):
        os.remove(new_file)
    else:
        os.replace(new_file, filename)

    sys.exit(0)

if (block := policy.policy("block_schema_sync")) is not None and block:
    print("==== Sync schema blocked by policy ====")
    sys.exit(0)

with open(filename, "r", encoding="UTF-8") as fd:
    save_schema = json.load(fd)


def get_column_type(prefix, column_data):
    query = prefix + f" {column_data['type']}"
    if "size" in column_data:
        query += f"({column_data['size']})"
    if "unsigned" in column_data and column_data["unsigned"]:
        query += " unsigned"
    if column_data["null"]:
        query += " default NULL"
    else:
        query += " NOT NULL"
        if "default" in column_data:
            if column_data['type'] in mysql.INTS:
                query += f" default {column_data['default']}"
            else:
                query += f" default \"{column_data['default']}\""
    return query


def run_query(query):
    if args.debug:
        print(">>>>", query)
    else:
        sql.sql_exec(query)


for table, table_data in save_schema.items():
    if table == ":more:":
        continue
    if table not in sql.schema:
        query = f"create table {table} "
        pfx = "( "
        for column, column_data in table_data["columns"].items():
            query += get_column_type(pfx + column + " ", column_data)
            pfx = ","
        run_query(query + ")")
        sql.schema[table] = {"columns": table_data["columns"], "indexes": {}}
        live_table = sql.schema[table]
    else:
        live_table = sql.schema[table]
        for column, column_data in table_data["columns"].items():
            if column not in live_table["columns"]:
                query = get_column_type(f"alter table {table} add column {column}", column_data)
                run_query(query)
            elif type_change(live_table["columns"][column], column_data):
                query = get_column_type(f"alter table {table} change column {column} {column}", column_data)
                run_query(query)

    if "indexes" not in table_data:
        continue

    for index, idx_data in table_data["indexes"].items():
        query = None
        if index not in live_table["indexes"]:
            unique = "index"
            if index == "PRIMARY" or index == ":primary:":
                unique = "primary key"
            elif "unique" in idx_data and idx_data["unique"]:
                unique = f"unique index {index}"
            else:
                unique = f"index {index}"
            query = f"alter table {table} add {unique} ({','.join(idx_data['columns'])})"
            run_query(query)
