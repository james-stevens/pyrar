#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from lib import registry

plugins = {}

def add_plugin(name, funcs):
    global plugins
    plugins[name] = funcs
    return True
