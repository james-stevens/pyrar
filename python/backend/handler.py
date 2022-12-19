#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

backend_plugins = {}

def add_plugin(name, funcs):
    global plugins
    backend_plugins[name] = funcs
    return True


def run(plugin_name, func_name):
    """ return the function named {func_name} in the set of handlers for {plugin_name} """
    if plugin_name not in backend_plugins or func_name not in backend_plugins[plugin_name]:
        return None
    return backend_plugins[plugin_name][func_name]
