#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

import os
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


def process_webhook(pay_module, sent_data):
    save_dir = os.path.join(os.environ["BASE"],"payments")
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", dir=save_dir, delete=False, prefix=pay_module + "_") as fd:
        fd.write(sent_data)

    if (func := pay_handler.run(pay_mod, "webhook")) is None:
        return False, f"Call to Webhook for '{pay_mod}' failed"

    if func(sent_data):
        return True, "Processed"
    else:
        return False, f"Webhook for'{pay_mod}' module is not set up"

    return False, f"Unknown failure for pay module '{pay_mod}'"


    return True, True


def main():
    log_init(with_debug=True)
    startup()
    print(json.dumps(config(), indent=3))
    print(pay_handler.pay_webhooks)


if __name__ == "__main__":
    main()
