#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import secrets
import base64
import hashlib
import bcrypt
import time
import os

from inspect import currentframe as czz, getframeinfo as gzz

import lib.mysql
from lib.event import event
import lib.validate as validate


def session_code(user_id):
    hsh = hashlib.sha512()
    hsh.update(secrets.token_bytes(500))
    hsh.update(str(user_id).encode("utf-8"))
    hsh.update(str(os.getpid()).encode("utf-8"))
    hsh.update(str(time.time()).encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")[:-2]


def session_key(session_code, user_agent):
    hsh = hashlib.sha512()
    hsh.update(session_code.encode("utf-8"))
    hsh.update(user_agent.encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")[:-2]


def register(data, user_agent):
    if data is None:
        return False, "Data missing"

    required = ["email", "password"]
    for item in required:
        if item not in data:
            return False, f"Missing data item '{item}'"

    if not validate.is_valid_email(data["email"]):
        return False, "Invalid email address"

    if lib.mysql.sql_exists("users", data, ["email"]):
        return False, "EMail address already in use"

    if "name" not in data:
        data["name"] = data["email"].split("@")[0]

    all_cols = required + ["name", "created_dt", "amended_dt"]

    data["password"] = bcrypt.hashpw(data["password"].encode("utf-8"),
                                     bcrypt.gensalt()).decode("utf-8")

    ret, user_id = lib.mysql.sql_insert("users", data, all_cols)
    if not ret:
        return False, "Registration failed"

    ret, user_data = lib.mysql.sql_get_one("users", {"user_id": user_id})
    if not ret:
        return False, "Registration failed"

    ses_code = session_code(user_id)
    lib.mysql.sql_insert(
        "session_keys", {
            "session_key": session_key(ses_code, user_agent),
            "user_id": user_id,
            "amended_dt": None,
            "created_dt": None
        })

    return True, {"user": user_data, "session": ses_code}


def test_fn():
    event({"notes": "some notes"}, gzz(czz()))


if __name__ == "__main__":
    lib.log.debug = True
    # print(register({"email":"james@jrcs.net","password":"my_password"}))
    # print(register({"e-mail":"james@jrcs.net","password":"my_password"}))
    print(session_code(100))
    print(session_key("fred", "Windows"))
    lib.mysql.connect("webui")
    test_fn()
