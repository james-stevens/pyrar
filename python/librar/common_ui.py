#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" used by both the user & admin ui's """

import json

from librar.policy import this_policy as policy
from librar import static
from librar.mysql import sql_server as sql
from librar import registry
from payments import libpay


def ui_config():
    full_conf = {
        "currency": policy.policy("currency"),
        "registry": registry.tld_lib.regs_send(),
        "dom_flags": static.CLIENT_DOM_FLAGS,
        "zones": registry.tld_lib.return_zone_list(),
        "status": static.DOMAIN_STATUS,
        "payment": libpay.config(),
        "policy": policy.data()
    }

    return full_conf


def main():
    sql.connect("webui")
    registry.start_up()
    print(json.dumps(ui_config(), indent=3))


if __name__ == "__main__":
    main()
