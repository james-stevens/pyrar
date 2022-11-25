#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import secrets
import base64
import hashlib
import bcrypt
import time
import os

from inspect import currentframe as czz, getframeinfo as gzz

import lib.mysql
import lib.validate as validate
from lib.policy import this_policy as policy


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


def remove_from_users(data):
    for block in ["password", "payment_data"]:
        del data[block]


def start_session(user_data,user_agent):
    user_id = user_data['user_id']
    lib.mysql.sql_exec(f"delete from session_keys where user_id = {user_id}")
    ses_code = session_code(user_id)
    lib.mysql.sql_insert(
        "session_keys", {
            "session_key": session_key(ses_code, user_agent),
            "user_id": user_id,
            "amended_dt": None,
            "created_dt": None
        })
    remove_from_users(user_data)
    return {"user": user_data, "session": ses_code}


def start_user_check(data):
    if data is None:
        return False, "Data missing"

    required = ["email", "password"]
    for item in required:
        if item not in data:
            return False, f"Missing data item '{item}'"

    if not validate.is_valid_email(data["email"]):
        return False, "Invalid email address"

    return True, None


def register(data, user_agent):
    ret, msg = start_user_check(data)
    if not ret:
        return ret, msg

    if lib.mysql.sql_exists("users", {"email": data["email"]}):
        return False, "EMail address already in use"

    if "name" not in data:
        data["name"] = data["email"].split("@")[0]

    all_cols = required + ["name", "created_dt", "amended_dt"]
    data.update({col: None for col in all_cols if col not in data})

    data["password"] = bcrypt.hashpw(data["password"].encode("utf-8"),
                                     bcrypt.gensalt()).decode("utf-8")

    ret, user_id = lib.mysql.sql_insert(
        "users", {item: data[item]
                  for item in all_cols})
    if ret == 1:
        return False, "Registration insert failed"

    ret, user_data = lib.mysql.sql_select_one("users", {"user_id": user_id})
    if not ret:
        return False, "Registration retrieve failed"

    return start_session(user_data,user_agent)


def check_session(ses_code, user_agent):
    key = session_key(ses_code, user_agent)
    hexkey = lib.mysql.ashex(key)
    session_timeout = policy.policy("session_timeout", 60)
    sql = "update session_keys set amended_dt=now() where date_add(amended_dt, interval "
    sql += f"{session_timeout} minute) > now() and session_key = unhex('{hexkey}')"

    ret, __ = lib.mysql.sql_exec(sql)
    if ret != 1:
        return False, None

    ret, ses_data = lib.mysql.sql_select_one("session_keys", {"session_key": key},"user_id")
    if ret != 1:
        return False, None

    ret, user_data = lib.mysql.sql_select_one("users",
                                           {"user_id": ses_data["user_id"]})
    if ret != 1:
        return False, None

    remove_from_users(user_data)
    return True, {"user": user_data, "session": ses_code}


def log_out(ses_code, user_id, user_agent):
    return lib.mysql.sql_delete_one("session_keys",{"session_key":session_key(ses_code, user_agent),"user_id":user_id})


def login(data, user_agent):
    ret, __ = start_user_check(data)
    if not ret:
        return None

    ret, user_data = lib.mysql.sql_select_one("users", {"email": data["email"]})
    if not ret:
        return None

    encoded_pass = user_data["password"].encode("utf8")
    enc_pass = bcrypt.hashpw(data["password"].encode("utf8"),encoded_pass)
    if encoded_pass != enc_pass:
        return None

    return start_session(user_data,user_agent)



if __name__ == "__main__":
    lib.mysql.connect("webui")
    lib.log.debug = True
    print(">>> LOGIN",login({"email":"james@jrcs.net","password":"pass"},"curl/7.83.1"))
    # print(register({"email":"james@jrcs.net","password":"my_password"}))
    # print(register({"e-mail":"james@jrcs.net","password":"my_password"}))
    # print(session_code(100))
    # print(session_key("fred", "Windows"))
    # print(
    #     check_session(
    #         "KhbceHALIcjrP4jquXeqAVESXE5bOTcBOor2UHPzHF0kRDJeaLgv1Li/uN1b7hOGWQFX5dq16RvWZp2vo7VI4A",
    #         "curl/7.83.1"))
    # print("DELETE",log_out("KhbceHALIcjrP4jquXeqAVESXE5bOTcBOor2UHPzHF0kRDJeaLgv1Li/uN1b7hOGWQFX5dq16RvWZp2vo7VI4A",10465,"curl/7.83.1"))
