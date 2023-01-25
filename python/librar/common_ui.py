#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar import registry
from librar.policy import this_policy as policy
from librar import  static_data
from librar import mysql as sql

from webui import pay_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from webui.pay_plugins import *

def ui_config():
    if (payment_methods := policy.policy("payment_methods")) is None:
        payment_methods = list(pay_handler.pay_plugins)

    return {
        "default_currency": policy.policy("currency"),
        "registry": registry.tld_lib.regs_send(),
        "dom_flags": static_data.CLIENT_DOM_FLAGS,
        "zones": registry.tld_lib.return_zone_list(),
        "status": static_data.DOMAIN_STATUS,
        "payments": {
            pay: pay_handler.pay_plugins[pay]["desc"]
            for pay in payment_methods if "desc" in pay_handler.pay_plugins[pay]
        },
        "policy": policy.data()
        }


def main():
    sql.connect("webui")
    registry.start_up()
    print(ui_config())


if __name__ == "__main__":
    main()
