#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import handler


def domain_create(epp_job):
    return True

def start_up_check():
    return True

def domain_update_from_db():
    return True

def domain_request_transfer():
    return True

def domain_renew():
    return True

def set_authcode():
    return True


def my_hello(__):
    return "LOCAL: Hello"


handler.add_plugin("local",{
    "hello": my_hello,
    "start_up": start_up_check,
    "dom/update": domain_update_from_db,
    "dom/create": domain_create,
    "dom/renew": domain_renew,
    "dom/transfer": domain_request_transfer,
    "dom/authcode": set_authcode
	})
