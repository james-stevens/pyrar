#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar import parsexml
from librar import mysql as sql

from webui import dom_handler


def local_domain_prices(domobj, num_years=1, qry_type=["create", "renew"], user_id=None):
    ok, reply = sql.sql_select("domains", {"name": domobj.names})
    if not ok:
        return False, "Unexpected database error"

    doms_db = {dom["name"]: dom for dom in reply}
    ret_js = []
    for dom in domobj.names if isinstance(domobj.names, list) else [domobj.names]:
        add_dom = {"num_years": num_years, "name": dom, "avail": False}
        for qt in qry_type:
            add_dom[qt] = None

        if dom not in doms_db:
            add_dom["avail"] = True
        else:
            this_dom = doms_db[dom]
            if this_dom["user_id"] == user_id:
                add_dom["yours"] = True
            add_dom["reason"] = "Already registered"
            if sql.has_data(this_dom, "for_sale_msg"):
                add_dom["avail"] = True
                add_dom["for_sale_msg"] = this_dom["for_sale_msg"]

        ret_js.append(add_dom)

    return True, ret_js


dom_handler.add_plugin("local", {"dom/price": local_domain_prices})
