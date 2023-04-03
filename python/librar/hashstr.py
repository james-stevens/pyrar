#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" hashing functions """

import sys
import os
import time
import secrets
import re
import hashlib
import base64
import base58


def make_hash(src_string=None, length=20):
    """ make general purpose random string """
    hsh = hashlib.sha256() if length <= 44 else hashlib.sha512()
    if src_string is None:
        hsh.update(secrets.token_bytes(500))
    else:
        hsh.update(src_string.encode("utf-8"))
    return base58.b58encode(hsh.digest()).decode("utf-8")[:length]


def make_session_code(user_id):
    """ make a user's session code - sent to the user """
    hsh = hashlib.sha256()
    hsh.update(secrets.token_bytes(500))
    hsh.update(str(user_id).encode("utf-8"))
    hsh.update(str(os.getpid()).encode("utf-8"))
    hsh.update(str(time.time()).encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")


def make_session_key(session_code, user_agent):
    """ make the user's session key from the code, this is the one stored """
    hsh = hashlib.sha256()
    hsh.update(session_code.encode("utf-8"))
    hsh.update(user_agent.encode("utf-8"))
    return base64.b64encode(hsh.digest()).decode("utf-8")


if __name__ == "__main__":
    print(make_hash(length=int(sys.argv[1]) if len(sys.argv) > 1 else 300))
