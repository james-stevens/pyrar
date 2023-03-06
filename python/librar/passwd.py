#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" password checking & encrypting fns """

import sys
import bcrypt


def crypt(text_password, salt=None):
    """ encrypt a password, using salt if provided """
    enc_passwd = text_password.encode("utf-8") if isinstance(text_password, str) else text_password
    salt = bcrypt.gensalt() if salt is None else salt.encode("utf8")
    return bcrypt.hashpw(enc_passwd, salt).decode("utf-8")


def compare(text_password, stored_password):
    """ return boolean if {text_password} matches {stored_password} """
    return crypt(text_password, stored_password) == stored_password


if __name__ == "__main__":
    print(">>>>", sys.argv[1], crypt(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    # print(">>>>", sys.argv[1], compare(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    # print(">>>>", sys.argv[1], crypt(base64.b64decode(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None))
