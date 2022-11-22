#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import bcrypt
import lib.mysql

def register(data):
    required = ["email","password"]
    for item in required:
        if item not in data:
            return False, "Insufficient data"

    all_cols = required
    data["password"] = bcrypt.hashpw(data["password"].encode("utf-8"),bcrypt.gensalt()).decode("utf-8")
    sql = lib.mysql.sql_insert("users",data,all_cols)
    return sql


if __name__ == "__main__":
    print(register({"email":"james@jrcs.net","password":"my_password"}))
    print(register({"e-mail":"james@jrcs.net","password":"my_password"}))
