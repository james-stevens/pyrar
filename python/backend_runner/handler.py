#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json

from lib import registry

plugins = {}
plugin_types_wanted = None


def add_plugin(name, funcs):
    global plugins
    plugins[name] = funcs
    return True
