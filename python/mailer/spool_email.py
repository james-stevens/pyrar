#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import os
import json
import tempfile

from librar.log import log, init as log_init
from librar.policy import this_policy as policy
from librar import mysql
from librar.mysql import sql_server as sql
from librar import registry
from librar import misc
from librar import hashstr

SPOOL_BASE = f"{os.environ['BASE']}/storage/perm/spooler"
ERROR_BASE = f"{os.environ['BASE']}/storage/perm/mail_error"
TEMPLATE_DIR = f"{os.environ['BASE']}/emails"

REQUIRE_FORMATTING = [
    "price_paid", "price_charged", "acct_current_balance", "amount", "pre_balance", "post_balance",
    "acct_current_balance", "acct_previous_balance", "acct_overdraw_limit", "acct_warn_low_balance", "for_sale_amount"
]


def event_log(prefix, records):
    email = records["user"]["email"] if "user" in records else None
    user_id = records["user"]["user_id"] if "user" in records else None
    domain_id = records["domain"]["domain_id"] if "domain" in records else None
    msg_type = records["email"]["message"] if "email" in records else None
    mysql.event_log({
        "event_type": f"{prefix}/{msg_type}",
        "domain_id": domain_id,
        "user_id": user_id,
        "who_did_it": "emailer",
        "from_where": "localhost",
        "notes": f"{prefix} message '{msg_type}' to '{email}'"
    })


def load_records(which_message, request_list):
    my_currency = policy.policy("currency")
    return_data = {"email": {"message": which_message}}
    for request in request_list:
        table = request[0]
        if table is None:
            return_data.update(request[1])
            continue

        ok, reply = sql.sql_select_one(table, request[1])

        if not ok or len(reply) <= 0:
            log(f"SPOOLER: Failed to load '{table}' where '{request[1]}'")
            return None

        for fmt in REQUIRE_FORMATTING:
            if fmt in reply and reply[fmt] is not None:
                reply[fmt + "_fmt"] = misc.format_currency(reply[fmt], my_currency)

        if table == "users":
            reply["hash_confirm"] = hashstr.make_hash(reply["created_dt"] + ":" + reply["email"])

        tag = request[3] if len(request) == 3 else table.rstrip("s")

        if table == "domains" and misc.has_data(reply, "name"):
            if (idn := misc.puny_to_utf8(reply["name"])) is not None:
                reply["display_name"] = idn
            else:
                reply["display_name"] = reply["name"]
            return_data["registry"] = registry.tld_lib.reg_record_for_domain(reply["name"])

        return_data[tag] = reply

    if "domain" in return_data and "sale" in return_data and "expiry_dt" in return_data[
            "domain"] and "num_years" in return_data["sale"]:
        return_data["domain"]["new_expiry_dt"] = misc.date_add(return_data["domain"]["expiry_dt"],
                                                               years=int(return_data["sale"]["num_years"]))

    return return_data


def spool(which_message, request_list):
    pfx = f"{TEMPLATE_DIR}/{which_message}"
    if not os.path.isfile(f"{pfx}.txt") and not os.path.isfile(f"{pfx}.html"):
        log(f"Warning: No email merge file found for type '{which_message}'")
        return False

    if (request_data := load_records(which_message, request_list)) is None:
        return False

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", dir=SPOOL_BASE, delete=False,
                                     prefix=which_message + "_") as fd:
        fd.write(json.dumps(request_data))

    event_log("Queued", request_data)
    return True


def debug_formatter():
    def_cur = policy.policy("currency")
    cur = {
        "desc": "Etherium",
        "iso": "ETH",
        "separator": [",", "."],
        "symbol": "\u039E",
        "decimal": 6,
    }

    print(misc.format_currency(int(sys.argv[1]), def_cur))
    print(misc.format_currency(int(sys.argv[1]), cur))
    sys.exit(0)


if __name__ == "__main__":
    log_init(with_debug=True)
    # debug_formatter()
    sql.connect("engine")
    registry.start_up()
    query = [["domains", {"name": "xn--e28h.xn--dp8h"}], ["users", {"email": "dan@jrcs.net"}]]
    # print("spool_email>>",spool_email("verify_email", query))
    spool("receipt", [[None, {
        "some-data": "value"
    }], ["sales", {
        "sales_item_id": 10535
    }], ["domains", {
        "domain_id": 10460
    }], ["users", {
        "user_id": 10450
    }]])
