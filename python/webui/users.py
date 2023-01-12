#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import secrets
import base64
import hashlib
import time
import os
import sys

from librar import mysql as sql
from librar import validate
from librar import passwd
from librar.policy import this_policy as policy
from librar.log import log, debug, init as log_init
from librar import hashstr

from mailer import spool_email

USER_REQUIRED = ["email", "password"]


def event_log(req, more_event_items):
    event_db = misc.where_event_log()
    event_db.update(req.base_event)
    event_db.update(more_event_items)
    sql.sql_insert("events", event_db)


def make_session_code(user_id):
    hsh = hashlib.sha256()
    hsh.update(secrets.token_bytes(500))
    hsh.update(str(user_id).encode("utf-8"))
    hsh.update(str(os.getpid()).encode("utf-8"))
    hsh.update(str(time.time()).encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")


def make_session_key(session_code, user_agent):
    hsh = hashlib.sha256()
    hsh.update(session_code.encode("utf-8"))
    hsh.update(user_agent.encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")


def start_session(user_db, user_agent):
    user_id = user_db['user_id']
    sql.sql_delete_one("session_keys", {"user_id": user_id})

    ses_code = make_session_code(user_id)
    sess_data = {"session_key": make_session_key(ses_code, user_agent), "user_id": user_id, "created_dt": None}

    ok, __ = sql.sql_insert("session_keys", sess_data)
    if not ok:
        return False, "Failed to start session"

    ret = {"user_id": user_id, "user": user_db, "session": ses_code}

    ok, orders_db = sql.sql_select("orders", {"user_id": user_id})
    if ok and len(orders_db) >= 1:
        ret["orders"] = orders_db

    return True, ret


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


def register(user_db, user_agent):
    ok, msg = start_user_check(user_db)
    if not ok:
        return ok, msg

    if sql.sql_exists("users", {"email": user_db["email"]}):
        return False, "EMail address already in use"

    if ("name" not in user_db) or (user_db["name"] == "") or (user_db["name"] is None):
        user_db["name"] = user_db["email"].split("@")[0]

    all_cols = USER_REQUIRED + ["name", "created_dt"]
    user_db.update({col: None for col in all_cols if col not in user_db})

    user_db["password"] = passwd.crypt(user_db["password"])
    ok, user_id = sql.sql_insert("users", {item: user_db[item] for item in all_cols})
    if not ok:
        return False, "Registration insert failed"

    update_user_login_dt(user_id)
    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok:
        return False, "Registration retrieve failed"

    return start_session(user_db, user_agent)


def check_session(ses_code, user_agent):
    if not validate.is_valid_ses_code(ses_code):
        return False, None

    key = make_session_key(ses_code, user_agent)
    tout = policy.policy('session_timeout')
    ok, data = sql.sql_select_one("session_keys", {"session_key": key},
                                  f"date_add(amended_dt, interval {tout} minute) > now() 'ok',user_id")

    if not ok:
        return False, None

    if "ok" not in data or not data["ok"]:
        sql.sql_delete_one("session_keys", {"session_key": key})
        return False, None

    sql.sql_update_one("session_keys", {}, {"session_key": key})

    return True, {"session": ses_code, "user_id": data["user_id"]}


def logout(ses_code, user_id, user_agent):
    ok = sql.sql_delete_one("session_keys", {
        "session_key": make_session_key(ses_code, user_agent),
        "user_id": user_id
    })
    if not ok:
        return False, "Logout failed"

    return True


def update_user_login_dt(user_id):
    sql.sql_update_one("users", {"last_login_dt": sql.now()}, {"user_id": int(user_id)})


def login(data, user_agent):
    ok, __ = start_user_check(data)
    if not ok:
        return False, None

    ok, user_db = sql.sql_select_one("users", {"account_closed": 0, "email": data["email"]})
    if not ok or not len(user_db):
        return False, None

    if not check_password(user_db["user_id"], data, user_db):
        return False, None

    update_user_login_dt(user_db['user_id'])
    log(f"USR-{user_db['user_id']} logged in")
    return start_session(user_db, user_agent)


USER_CAN_CHANGE = {
    "default_auto_renew": validate.validate_binary,
    "email": validate.is_valid_email,
    "name": validate.is_valid_display_name
}


def update_user(user_id, post_json):
    for item in post_json:
        if item not in USER_CAN_CHANGE or not USER_CAN_CHANGE[item](post_json[item]):
            return False, f"Invalid data item - '{item}'"

    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok:
        return False, "Failed to load user"

    if "email" in post_json and user_db["email"] != post_json["email"]:
        post_json["email_verified"] = 0

    ok = sql.sql_update_one("users", post_json, {"user_id": user_id})
    if not ok:
        return False, "Failed to update user"

    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok:
        return False, "Failed to load user"

    return ok, user_db


def check_password(user_id, data, user_db=None):
    if not sql.has_data(data, "password"):
        return False

    if user_db is None:
        ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
        if not ok:
            return False

    return passwd.compare(data["password"], user_db["password"])


def verify_email(user_id, hash_sent):
    ok, user_db = sql.sql_select_one("users", {"user_id": user_id})
    if not ok:
        return False
    hash_found = hashstr.hash_confirm(user_db["created_dt"] + ":" + user_db["email"])
    if hash_found == hash_sent:
        return sql.sql_update_one("users", {
            "email_verified": True,
            "amended_dt": None
        }, {"user_id": user_db["user_id"]})
    return False


def request_password_reset(req):
    email = req.post_js["email"]
    pin_num = req.post_js["pin"]
    if not validate.is_valid_email(email) or not validate.is_valid_pin(pin_num):
        return False
    ok, user_db = sql.sql_select_one("users", {"account_closed": 0, "email": email})
    if not ok or not len(user_db):
        return None

    send_hash = make_session_code(user_db["user_id"])[:30]
    store_hash = hashstr.make_hash(f"{send_hash}:{pin_num}", 30)
    if not sql.sql_update_one("users", {"password_reset": store_hash}, {"user_id": user_db["user_id"]}):
        return None

    spool_email.spool("reset_request", [["users", {"user_id": user_db["user_id"]}], [None, {"reset_code": send_hash}]])
    return send_hash


def reset_users_password(req):
    send_hash = req.post_js["code"]
    pin_num = req.post_js["pin"]
    new_password = req.post_js["password"]
    if not validate.is_valid_pin(pin_num) or len(send_hash) != 30:
        return False

    store_hash = hashstr.make_hash(f"{send_hash}:{pin_num}", 30)
    ok, user_db = sql.sql_select_one("users", {"account_closed": 0, "password_reset": store_hash})
    if not ok or not len(user_db):
        return False

    if not sql.sql_update_one("users", {
            "password": passwd.crypt(new_password),
            "password_reset": None
    }, {"user_id": user_db["user_id"]}):
        return False

    spool_email.spool("password_reset", [["users", {"user_id": user_db["user_id"]}]])
    return True


class Empty:
    pass


if __name__ == "__main__":
    sql.connect("webui")
    log_init(with_debug=True)

    req = Empty()
    req.post_js = {}
    req.post_js["email"] = "dan@jrcs.net"
    req.post_js["pin"] = "1234"
    send_hash = request_password_reset(req)
    print(">>> Ask-RESET", send_hash)
    #print(">>>  Do-RESET", reset_users_password(send_hash, 1234, "aa"))

    sys.exit(0)
    # login_ok, login_data = login({"email": "flip@flop.com", "password": "aa"}, "curl/7.83.1")
    # debug(">>> LOGIN " + str(login_ok) + "/" + str(login_data))
    # print(register({"email":"james@jrcs.net","password":"my_password"}))
    # print(register({"e-mail":"james@jrcs.net","password":"my_password"}))
    # print(make_session_code(100))
    # print(make_session_key("fred", "Windows"))
    debug(">>>>SELECT " +
          str(sql.sql_select("session_keys", "1=1", "date_add(amended_dt, interval 60 minute) > now() 'ok',user_id")))
    debug(">>>> " + str(login_data["session"]))
    debug(">>>>CHECK-SESSION " + str(check_session(login_data["session"], "curl/7.83.1")))
