#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

import os
import json
import tempfile

from librar import misc
from librar.log import log, init as log_init
from librar.mysql import sql_server as sql
from mailer import spool_email
from payments import payfuncs

from payments import pay_handler
from payments.plugins import *

HAS_RUN_START_UP = False


def startup():
    global HAS_RUN_START_UP
    pay_conf = payfuncs.payment_file.data()
    for module in [mod for mod in pay_conf if mod in pay_handler.pay_plugins]:
        if (func := pay_handler.run(module, "startup")) is not None and func():
            this_conf = pay_conf[module]
            my_mode = this_conf["mode"] if "mode" in this_conf else "live"
            if my_mode in this_conf and "webhook" in this_conf[my_mode]:
                this_mode = this_conf[my_mode]
                this_mode["name"] = module
                this_mode["mode"] = my_mode
                pay_handler.pay_webhooks[this_mode["webhook"]] = this_mode
    HAS_RUN_START_UP = True


def config():
    if not HAS_RUN_START_UP:
        startup()

    all_config = {}
    for module in [mod for mod in payfuncs.payment_file.data() if mod in pay_handler.pay_plugins]:
        all_config[module] = None
        if (func := pay_handler.run(module, "config")) is not None:
            all_config[module] = func()
    return all_config


def process_webhook(headers, webhook_data, sent_data):
    if not misc.has_data(webhook_data,["name","mode","webhook"]):
        return False, "Webhook data is invalid"

    pay_module = webhook_data["name"]
    file_name = None
    with tempfile.NamedTemporaryFile("w+",
                                     encoding="utf-8",
                                     dir=misc.make_year_month_day_dir(
                                         os.path.join(os.environ["BASE"], "storage/perm/payments")),
                                     delete=False,
                                     prefix=pay_module + "_") as fd:
        file_name = fd.name
        os.chmod(file_name, 0o755)
        if isinstance(sent_data, str):
            fd.write(sent_data)
        else:
            json.dump(sent_data, fd)

    if (func := pay_handler.run(pay_module, "webhook")) is None:
        return False, f"Webhook for'{pay_module}' module is not set up"

    ok, reply = func(headers, webhook_data, sent_data, file_name)
    if ok is None and reply is None:
        os.remove(file_name)
        return True, True

    if ok:
        return True, True

    if file_name is not None:
        spool_email.spool("admin_webhook_failed",
                          [[None, {
                              "filename": file_name,
                              "pay_module": pay_module,
                              "message": reply
                          }]])

    log(f"WebHook Processing Error - {reply}")
    return False, f"Call to Webhook for '{pay_module}' failed"


def main():
    log_init(with_debug=True)
    sql.connect("engine")
    startup()
    print(json.dumps(config(),indent=3))
    print(json.dumps(pay_handler.pay_webhooks,indent=3))


if __name__ == "__main__":
    main()
