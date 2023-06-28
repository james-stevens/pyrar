#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" run job requests queued in table `backend` """

from librar.log import log
from librar import registry

from backend import dom_handler
from backend.dom_plugins import *

JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}


def has_func(action, dom, bke_job):
    if dom.registry["type"] not in dom_handler.backend_plugins:
        return None, (f"ERROR: Registry '{dom.registry['name']}' type '{dom.registry['type']}'" +
                      " for '{dom.dom_db['name']}' not supported")
    this_handler = dom_handler.backend_plugins[dom.registry["type"]]
    return action in this_handler and this_handler[action] is not None, None


def run(action, dom, bke_job):
    this_handler = dom_handler.backend_plugins[dom.registry["type"]]
    return this_handler[action](bke_job, dom)


def get_prices(domlist, num_years, qry_type):
    this_handler = dom_handler.backend_plugins[domlist.registry["type"]]
    if "dom/price" not in this_handler:
        log(f"ERROR: Action 'dom/price' not supported by Plugin '{domlist.reg['type']}'")
        return False, f"Action 'dom/price' not supported by plugin '{domlist.reg['type']}'"
    return this_handler["dom/price"](domlist, num_years, qry_type)


def start_ups():
    """ for each plug-in, if we use it, run its start-up """
    all_regs = registry.tld_lib.regs_file.data()
    have_types = {reg_data["type"]: True for __, reg_data in all_regs.items() if "type" in reg_data}
    for this_type, funcs in dom_handler.backend_plugins.items():
        if this_type in have_types and "start_up" in funcs:
            funcs["start_up"]()
