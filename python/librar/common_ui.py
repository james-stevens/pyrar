#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" used by both the user & admin ui's """

from payments import pay_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from payments.plugins import *

from librar.policy import this_policy as policy
from librar import static
from librar import mysql as sql
from librar import registry


def ui_config():
    if (payment_methods := policy.policy("payment_methods")) is None:
        payment_methods = list(pay_handler.pay_plugins)

    full_conf = {
        "currency": policy.policy("currency"),
        "registry": registry.tld_lib.regs_send(),
        "dom_flags": static.CLIENT_DOM_FLAGS,
        "zones": registry.tld_lib.return_zone_list(),
        "status": static.DOMAIN_STATUS,
        "payment": {
            pay: pay_handler.pay_plugins[pay]["desc"]
            for pay in payment_methods if "desc" in pay_handler.pay_plugins[pay]
        },
        "policy": policy.data()
    }

    pay_conf = pay_handler.payment_file.data()
    if isinstance(pay_conf,dict) and "paypal" in pay_conf:
        payapl_conf = pay_conf["paypal"]
        paypal_mode = payapl_conf["mode"] if "mode" in payapl_conf else "live"
        if paypal_mode in payapl_conf and "client_id" in payapl_conf[paypal_mode]:
            full_conf["paypal_client_id"] = payapl_conf[paypal_mode]["client_id"]
        elif "client_id" in payapl_conf:
            full_conf["paypal_client_id"] = payapl_conf["client_id"]

    return full_conf



def main():
    sql.connect("webui")
    registry.start_up()
    print(ui_config())


if __name__ == "__main__":
    main()
