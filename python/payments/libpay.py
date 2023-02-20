#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

import json

from librar.log import log, debug, init as log_init
from payments import payfile

from payments import pay_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from payments.plugins import *

HAS_RUN_START_UP = False


def startup():
    global HAS_RUN_START_UP
    for module in [mod for mod in payfile.payment_file.data() if mod in pay_handler.pay_plugins]:
        if (func := pay_handler.run(module, "startup")) is not None:
            func()
    HAS_RUN_START_UP = True


def config():
    if not HAS_RUN_START_UP:
        startup()

    all_config = {}
    for module in [mod for mod in payfile.payment_file.data() if mod in pay_handler.pay_plugins]:
        all_config[module] = None
        if (func := pay_handler.run(module, "config")) is not None:
            all_config[module] = func()
    return all_config


def process_webhook(webhook):
    return True


def main():
    log_init(with_debug=True)
    startup()
    print(json.dumps(config(), indent=3))
    print(pay_handler.pay_webhooks)


if __name__ == "__main__":
    main()
