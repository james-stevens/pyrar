#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" password checking & encrypting fns """

import sys
import bcrypt
import argon2


def crypt_argon2(text_password):
    """ encrypt a password, using salt if provided """
    ph = argon2.PasswordHasher()
    return ph.hash(text_password)


def compare_argon2(text_password, stored_password):
    """ return boolean if {text_password} matches {stored_password} """
    ph = argon2.PasswordHasher()
    try:
        ph.verify(stored_password, text_password)
        return True
    except Exception:
        return False


def crypt_bcrypt(text_password, salt=None):
    """ encrypt a password, using salt if provided """
    enc_passwd = text_password.encode("utf-8") if isinstance(text_password, str) else text_password
    salt = bcrypt.gensalt() if salt is None else salt.encode("utf8")
    return bcrypt.hashpw(enc_passwd, salt).decode("utf-8")


def compare_bcrypt(text_password, stored_password):
    """ return boolean if {text_password} matches {stored_password} """
    return crypt_bcrypt(text_password, stored_password) == stored_password


def needs_updating(stored_password):
    split_password = stored_password.split("$")
    return split_password[1] != "argon2id"


def compare(text_password, stored_password):
    split_password = stored_password.split("$")
    if split_password[1] == "2b":
        return compare_bcrypt(text_password, stored_password)
    elif split_password[1] == "argon2id":
        return compare_argon2(text_password, stored_password)
    return False


def crypt(text_password):
    return crypt_argon2(text_password)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print(">>>2>>>", sys.argv[1], sys.argv[2], compare(sys.argv[1], sys.argv[2]))
    else:
        print(">>>1>>>", sys.argv[1], crypt(sys.argv[1]))
        print(">>>1a>>>", sys.argv[1], crypt_argon2(sys.argv[1]))
        print(">>>1b>>>", sys.argv[1], crypt_bcrypt(sys.argv[1]))
