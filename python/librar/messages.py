#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" code for messaging user """

from librar.mysql import sql_server as sql


def send(user_id, message):
    """ send {message} to {user_id} """
    sql.sql_insert("messages", {"user_id": user_id, "message": message, "is_read": False})
