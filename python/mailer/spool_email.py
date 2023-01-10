#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import datetime
import tempfile

from librar.log import log, debug, init as log_init
from librar import mysql as sql
from librar import registry
from librar import misc
from librar import hashstr

SPOOL_BASE = f"{os.environ['BASE']}/storage/perm/spooler"
ERROR_BASE = f"{os.environ['BASE']}/storage/perm/mail_error"
TEMPLATE_DIR = f"{os.environ['BASE']}/emails"

def load_records(which_message, request_list):
    return_data = {"email": {"message": which_message}}
    for request in request_list:
        table = request[0]
        ok, reply = sql.sql_select_one(table, request[1])

        if not ok or len(reply) <= 0:
            log(f"SPOOLER: Failed to load '{table}' where '{request[1]}'")
            return None

        if table == "users":
            if not reply["email_verified"] and which_message != "verify_email":
                return None
            reply["hash_confirm"] = hashstr.hash_confirm(reply["created_dt"]+":"+reply["email"])

        tag = request[3] if len(request) == 3 else table.rstrip("s")

        if table == "domains" and sql.has_data(reply, "name"):
            if (idn := misc.puny_to_utf8(reply["name"])) is not None:
                reply["display_name"] = idn
            else:
                reply["display_name"] = reply["name"]
            return_data["registry"] = registry.tld_lib.reg_record_for_domain(reply["name"])

        return_data[tag] = reply

    return return_data


def spool(which_message, request_list):
    if not os.path.isfile(f"{TEMPLATE_DIR}/{which_message}.txt"):
        return False

    if (request_data := load_records(which_message, request_list)) is None:
        return False

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", dir=SPOOL_BASE, delete=False,
                                     prefix=which_message + "_") as fd:
        fd.write(json.dumps(request_data))

    return True


if __name__ == "__main__":
    log_init(with_debug=True)
    sql.connect("engine")
    registry.start_up()
    print("spool_email>>",spool_email("verify_email", [["domains", {"name": "xn--e28h.xn--dp8h"}], ["users", {"email": "dan@jrcs.net"}]]))
