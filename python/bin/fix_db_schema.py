#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" update this schema to match etc/schema """

import json
import os
import sys
import argparse
import filecmp

from librar import mysql as sql
from librar import schema
from librar.policy import this_policy as policy

SCHEMA_FILE = f"{os.environ['BASE']}/python/etc/schema.json"


def type_change(col1, col2):
    """ check to see if the column type or size has changed """
    if col1["type"] != col2["type"]:
        return True
    if "size" in col1 or "size" in col2:
        if "size" in col1 and "size" not in col2:
            return True
        if "size" in col2 and "size" not in col1:
            return True
        if col1["size"] != col2["size"]:
            return True
    if "null" in col1 or "null" in col2:
        if "null" in col1 and "null" not in col2:
            return True
        if "null" in col2 and "null" not in col1:
            return True
        if col1["null"] != col2["null"]:
            return True

    return False


parser = argparse.ArgumentParser(description='EPP Jobs Runner')
parser.add_argument("-C", '--recreate', action="store_true")
args = parser.parse_args()

sql.connect("admin")
live_schema = schema.make_schema(sql.my_database)

if args.recreate:
    new_file = SCHEMA_FILE + ".new"
    if os.path.isfile(new_file):
        os.remove(new_file)

    with open(new_file, "w", encoding="UTF-8") as fd:
        fd.write(json.dumps(live_schema, indent=3))

    if filecmp.cmp(new_file, SCHEMA_FILE):
        os.remove(new_file)
    else:
        os.replace(new_file, SCHEMA_FILE)

    sys.exit(0)

if (block := policy.policy("block_schema_sync")) is not None and block:
    print("==== Sync schema blocked by policy ====")
    sys.exit(0)

with open(SCHEMA_FILE, "r", encoding="UTF-8") as fd:
    save_schema = json.load(fd)

for table, table_data in save_schema.items():
    live_table = live_schema[table]
    for column, column_data in table_data["columns"].items():
        query = None

        if column not in live_table["columns"]:
            query = f"alter table {table} add column {column}"
        elif type_change(live_table["columns"][column], column_data):
            query = f"alter table {table} change column {column} {column}"

        if query is not None:
            query += f" {column_data['type']}"
            if "size" in column_data:
                query += f"({column_data['size']})"
            if column_data["null"]:
                query += " default NULL"
            else:
                query += " NOT NULL"
                if "default" in column_data:
                    if column_data['type'] in schema.numbers:
                        query += f" default {column_data['default']}"
                    else:
                        query += f" default \"{column_data['default']}\""
            sql.sql_exec(query)

    for index, idx_data in table_data["indexes"].items():
        query = None
        if index not in live_table["indexes"]:
            unique = "index"
            if "unique" in idx_data and idx_data["unique"]:
                unique = "unique index"
            query = f"create {unique} {index} on {table} ({'.'.join(idx_data['columns'])})"
            sql.sql_exec(query)
