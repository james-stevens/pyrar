#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import secrets
import base64
import hashlib
import time
import os
from inspect import currentframe as czz, getframeinfo as gzz
import bcrypt

from lib import mysql as sql
from lib import validate
from lib.policy import this_policy as policy
from lib.log import log, debug, init as log_init

USER_REQUIRED = ["email", "password"]


def make_session_code(user_id):
    hsh = hashlib.sha512()
    hsh.update(secrets.token_bytes(500))
    hsh.update(str(user_id).encode("utf-8"))
    hsh.update(str(os.getpid()).encode("utf-8"))
    hsh.update(str(time.time()).encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")[:-2]


def make_session_key(session_code, user_agent):
    hsh = hashlib.sha512()
    hsh.update(session_code.encode("utf-8"))
    hsh.update(user_agent.encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")[:-2]


def remove_from_users(data):
    for block in ["password", "payment_data"]:
        del data[block]


def start_session(user_data, user_agent):
    user_id = user_data['user_id']
    sql.sql_delete_one("session_keys", {"user_id": user_id})

    ses_code = make_session_code(user_id)
    sql.sql_insert(
        "session_keys", {
            "session_key": make_session_key(ses_code, user_agent),
            "user_id": user_id,
            "amended_dt": None,
            "created_dt": None
        })
    remove_from_users(user_data)
    return True, {"user": user_data, "session": ses_code}


def start_user_check(data):
    if data is None:
        return False, "Data missing"

    for item in USER_REQUIRED:
        if item not in data:
            return False, f"Missing data item '{item}'"

    if not validate.is_valid_email(data["email"]):
        return False, "Invalid email address"

    if "name" in data and not validate.is_valid_display_name(data["name"]):
        return False, "Invalid display name"

    return True, None


def register(data, user_agent):
    ret, msg = start_user_check(data)
    if not ret:
        return ret, msg

    if sql.sql_exists("users", {"email": data["email"]}):
        return False, "EMail address already in use"

    if "name" not in data and data["email"].find("@") >= 0:
        data["name"] = data["email"].split("@")[0]

    all_cols = USER_REQUIRED + ["name", "created_dt", "amended_dt"]
    data.update({col: None for col in all_cols if col not in data})

    data["password"] = bcrypt.hashpw(data["password"].encode("utf-8"),
                                     bcrypt.gensalt()).decode("utf-8")

    ret, user_id = sql.sql_insert("users",
                                  {item: data[item]
                                   for item in all_cols})
    if not ret:
        return False, "Registration insert failed"

    ret, user_data = sql.sql_select_one("users", {"user_id": user_id})
    if not ret:
        return False, "Registration retrieve failed"

    return start_session(user_data, user_agent)


def check_session(ses_code, user_agent):
    if not validate.is_valid_ses_code(ses_code):
        return False, None

    key = make_session_key(ses_code, user_agent)
    tout = policy.policy('session_timeout', 60)
    cols = f"date_add(amended_dt, interval {tout} minute) > now() 'ok',user_id"
    ret, data = sql.sql_select_one("session_keys", {"session_key": key}, cols)
    if not ret:
        return False, None
    if not data["ok"]:
        sql.sql_delete_one("session_keys", {"session_key": key})
        return False, None

    sql.sql_update_one("session_keys", {"amended_dt": None},
                       {"session_key": key})

    ret, user_data = sql.sql_select_one("users", {"user_id": data["user_id"]})
    if not ret:
        return False, None

    remove_from_users(user_data)
    return True, {"user": user_data, "session": ses_code}


def logout(ses_code, user_id, user_agent):
    return sql.sql_delete_one(
        "session_keys", {
            "session_key": make_session_key(ses_code, user_agent),
            "user_id": user_id
        })


def login(data, user_agent):
    ret, __ = start_user_check(data)
    if not ret:
        return False, None

    ret, user_data = sql.sql_select_one("users", {"email": data["email"]})
    if not ret:
        return False, None

    encoded_pass = user_data["password"].encode("utf8")
    enc_pass = bcrypt.hashpw(data["password"].encode("utf8"), encoded_pass)
    if encoded_pass != enc_pass:
        return False, None

    log("User {user_data['user']['user_id']} logged in", gzz(czz()))
    return start_session(user_data, user_agent)


if __name__ == "__main__":
    sql.connect("webui")
    log_init(debug=True)
    login_ok, login_data = login(
        {
            "email": "james@jrcs.net",
            "password": "pass"
        }, "curl/7.83.1")
    debug(">>> LOGIN " + str(login_ok) + "/" + str(login_data), gzz(czz()))
    # print(register({"email":"james@jrcs.net","password":"my_password"}))
    # print(register({"e-mail":"james@jrcs.net","password":"my_password"}))
    # print(make_session_code(100))
    # print(make_session_key("fred", "Windows"))
    debug(
        ">>>>SELECT " + str(
            sql.sql_select(
                "session_keys", "1=1",
                "date_add(amended_dt, interval 60 minute) > now() 'ok',user_id"
            )), gzz(czz()))
    debug(">>>> " + str(login_data["session"]), gzz(czz()))
    debug(
        ">>>>CHECK-SESSION " +
        str(check_session(login_data["session"], "curl/7.83.1")), gzz(czz()))
