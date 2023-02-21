#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

import os
import json
import tempfile
import datetime

from librar.log import log, debug, init as log_init
from mailer import spool_email
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
    save_dir = os.path.join(os.environ["BASE"], "storage/perm/payments")
    for dir in datetime.datetime.now().strftime("%Y,%m,%d").split(","):
        save_dir = os.path.join(save_dir, dir)
        if not os.path.isdir(save_dir):
            os.mkdir(save_dir)
            os.chmod(save_dir, 0o777)

    file_name = None
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", dir=save_dir, delete=False,
                                     prefix=pay_module + "_") as fd:
        file_name = fd.name
        os.chmod(file_name, 0o755)
        if isinstance(sent_data, str):
            fd.write(sent_data)
        else:
            json.dump(sent_data, fd)

    if (func := pay_handler.run(pay_module, "webhook")) is None:
        return False, f"Webhook for'{pay_module}' module is not set up"

    ok, reply = func(sent_data)
    if ok:
        return True, "Processed"

    if file_name is not None:
        spool_email.spool("admin_webhook_failed",
                          [[None, {
                              "filename": file_name,
                              "pay_module": pay_module,
                              "message": reply
                          }]])

    return False, f"Call to Webhook for '{pay_module}' failed"


def main():
    log_init(with_debug=True)
    startup()
    print(json.dumps(config(), indent=3))
    print(pay_handler.pay_webhooks)


if __name__ == "__main__":
    main()