#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" run job requests queued in table `backend` """

from librar.log import log
from librar import registry

from backend import dom_handler
from backend.dom_plugins import *

JOB_RESULT = {None: "FAILED", False: "Retry", True: "Complete"}


def run(action, this_reg, bke_job, dom_db):
    this_handler = dom_handler.backend_plugins[this_reg["type"]]
    if action not in this_handler:
        log(f"Action '{action}' not supported by Plugin '{this_reg['type']}'")
        return None
    return this_handler[action](this_reg, bke_job, dom_db)


def get_prices(domlist, num_years, qry_type):
    this_handler = dom_handler.backend_plugins[domlist.registry["type"]]
    if "dom/price" not in this_handler:
        log(f"Action 'dom/price' not supported by Plugin '{domlist.reg['type']}'")
        return False, f"Action 'dom/price' not supported by plugin '{domlist.reg['type']}'"
    return this_handler["dom/price"](domlist, num_years, qry_type)


def start_ups():
    """ for each plug-in, if we use it, run its start-up """
    all_regs = registry.tld_lib.regs_file.data()
    have_types = {reg_data["type"]: True for __, reg_data in all_regs.items() if "type" in reg_data}
    for this_type, funcs in dom_handler.backend_plugins.items():
        if this_type in have_types and "start_up" in funcs:
            funcs["start_up"]()
