#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

from payments import payfuncs

pay_plugins = {}
pay_webhooks = {}


def add_plugin(name, funcs):
    """ Add dict of {funcs} as handlers for plugin module {name}"""
    global pay_plugins
    pay_plugins[name] = funcs


def run(plugin_name, func_name):
    """ return the function named {func_name} in the set of handlers for {plugin_name} """
    if plugin_name not in pay_plugins or func_name not in pay_plugins[plugin_name]:
        return None
    pay_conf = payfuncs.payment_file.data()
    if plugin_name not in pay_conf:
        return None
    return pay_plugins[plugin_name][func_name]


def module_config(this_module):
    pay_conf = payfuncs.payment_file.data()
    if pay_conf is None or not isinstance(pay_conf, dict) or this_module not in pay_conf:
        return None, None
    my_conf = pay_conf[this_module]
    my_mode = my_conf["mode"] if "mode" in my_conf else "live"
    if my_mode not in my_conf:
        return None
    ret_conf = my_conf[my_mode]
    ret_conf["mode"] = my_mode
    return ret_conf
