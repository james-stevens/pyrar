#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

ui_plugins = {}


def add_plugin(name, funcs):
    """ Add dict of {funcs} as handlers for plugin module {name}"""
    global ui_plugins
    ui_plugins[name] = funcs


def run(plugin_name, func_name):
    """ return the function named {func_name} in the set of handlers for {plugin_name} """
    if plugin_name not in ui_plugins or func_name not in ui_plugins[plugin_name]:
        return None
    return ui_plugins[plugin_name][func_name]
