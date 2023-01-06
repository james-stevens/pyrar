#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import datetime
import tempfile

from librar import mysql as sql
from librar import registry

SPOOL_BASE = f"{os.environ['BASE']}/storage/perm/spooler"
ERROR_BASE = f"{os.environ['BASE']}/storage/perm/mail_error"
TEMPLATE_DIR = f"{os.environ['BASE']}/emails"


def load_records(which_message, request_list):
    return_data = {"email": {"message": which_message}}
    for request in request_list:
        ok, reply = sql.sql_select_one(request[0], request[1])
        if len(request) == 3:
            tag = request[3]
        else:
            tag = request[0].rstrip("s")

        if request[0] == "domains" and sql.has_data(reply, "name"):
            reply["display_name"] = reply["name"].encode("utf-8").decode("idna")
            return_data["registry"] = registry.tld_lib.reg_record_for_domain(reply["name"])

        return_data[tag] = reply

    return return_data


def spool_email(which_message, request_list):
    if not os.path.isfile(f"{TEMPLATE_DIR}/{which_message}.txt"):
        return False

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", dir=SPOOL_BASE, delete=False,
                                     prefix=which_message + "_") as fd:
        fd.write(json.dumps(load_records(which_message, request_list)))

    return True


if __name__ == "__main__":
    sql.connect("engine")
    registry.start_up()
    spool_email("reminder", [["domains", {"name": "xn--e28h.xn--dp8h"}], ["users", {"email": "flip@flop.com"}]])
