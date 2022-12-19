#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import bcrypt
import base64


def crypt(text_password, salt=None):
    if isinstance(text_password, str):
        enc_passwd = text_password.encode("utf-8")
    else:
        enc_passwd = text_password

    if salt is None:
        salt = bcrypt.gensalt()
    else:
        salt = salt.encode("utf8")
    return bcrypt.hashpw(enc_passwd, salt).decode("utf-8")


def compare(text_password, stored_password):
    return crypt(text_password, stored_password) == stored_password


if __name__ == "__main__":
    print(">>>>", sys.argv[1], crypt(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    print(">>>>", sys.argv[1], compare(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    print(">>>>", sys.argv[1], crypt(base64.b64decode(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None))
