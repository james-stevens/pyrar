#! /usr/bin/python3
#################################################################
#    (c) Copyright 2009-2022 JRCS Ltd  - All Rights Reserved    #
#################################################################

import json
import os
from librar import mysql as sql

numbers = {"tinyint", "int", "decimal"}

def sortElm(i):
    return i["Field"]


def make_schema(database):
    schema = {}

    sql.cnx.query("show tables")
    res = sql.cnx.store_result()
    ret = res.fetch_row(maxrows=0, how=1)

    n = "Tables_in_" + database

    schema = {t[n]: {} for t in ret}

    for t in schema:
        sql.cnx.query("describe " + t)
        res = sql.cnx.store_result()
        ret = res.fetch_row(maxrows=0, how=1)
        schema[t]["columns"] = {}
        cols = [r for r in ret]
        cols.sort(key=sortElm)
        for r in cols:

            schema[t]["columns"][r["Field"]] = {}
            tp = r["Type"]
            if tp.find(" unsigned") >= 0:
                tp = tp.split()[0]
                schema[t]["columns"][r["Field"]]["unsigned"] = True

            pos = tp.find("(")
            if pos >= 0:
                sz = tp[pos + 1:-1]
                if sz[-2:] == ",0":
                    sz = sz[:-2]
                schema[t]["columns"][r["Field"]]["size"] = int(sz)
                tp = tp[:pos]

            schema[t]["columns"][r["Field"]]["type"] = tp
            if r["Extra"] == "auto_increment":
                schema[t]["columns"][r["Field"]]["serial"] = True

            schema[t]["columns"][r["Field"]]["null"] = r["Null"] == "YES"
            if r["Default"] is not None:
                if tp in numbers:
                    schema[t]["columns"][r["Field"]]["default"] = int(r["Default"])
                else:
                    schema[t]["columns"][r["Field"]]["default"] = r["Default"]

        sql.cnx.query("show index from " + t)
        res = sql.cnx.store_result()
        ret = res.fetch_row(maxrows=0, how=1)
        schema[t]["indexes"] = {}
        for r in ret:
            if r["Key_name"] not in schema[t]["indexes"]:
                schema[t]["indexes"][r["Key_name"]] = {}
                schema[t]["indexes"][r["Key_name"]]["columns"] = []
            schema[t]["indexes"][r["Key_name"]]["columns"].append(r["Column_name"])
            schema[t]["indexes"][r["Key_name"]]["unique"] = r["Non_unique"] == 0

    return schema
