#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json
import lib.mysql

# from inspect import currentframe as czz, getframeinfo as gzz

extra_data = {}


def http_start(who_did_it, from_where, user_id):
    global extra_data
    extra_data["from_where"] = from_where
    extra_data["user_id"] = user_id
    extra_data["who_did_it"] = who_did_it


def event(data, frameinfo):
    data["program"] = frameinfo.filename.split("/")[-1]
    data["function"] = frameinfo.function
    data["line_num"] = frameinfo.lineno
    data["when_dt"] = None
    data.update(extra_data)
    lib.mysql.sql_insert("events", data)
