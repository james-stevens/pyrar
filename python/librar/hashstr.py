#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import os
import time
import secrets
import re
import hashlib
import base64


def make_hash(src_string, chars_needed=20):
    hsh = hashlib.sha256()
    hsh.update(src_string.encode("utf-8"))
    return re.sub("[+/.=]", "", base64.b64encode(hsh.digest()).decode("utf-8"))[:chars_needed]


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


if __name__ == "__main__":
    print(make_hash(make_session_code(100),30))
