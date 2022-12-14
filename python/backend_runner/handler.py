#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import json

from lib import registry


plugins = {}
plugin_types_wanted = None


def add_plugin(name,funcs):
    global plugins
    plugins[name] = funcs
    return True


def start_up():
    global plugin_types_wanted
    plugin_types_wanted = { reg["type"]:True for __, reg in registry.tld_lib.registry.items() }
    for reg_type, __ in plugins.items():
        if reg_type not in plugin_types_wanted:
            del plugins[reg_type]


if __name__ == "__main__":
    add_plugin("epp",{"test":1})
    print("REGISTRY", json.dumps(registry.tld_lib.registry, indent=3))
    print("REGTYPE", json.dumps(plugin_types_wanted, indent=3))
    print("PLUGINS", json.dumps(plugins, indent=3))
