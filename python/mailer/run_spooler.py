#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import os
import json
import jinja2
import datetime
import time
import smtplib
import argparse

from librar import mysql as sql
from librar import flat
from librar import registry
from librar import policy
from librar.log import log, debug, init as log_init

from email.message import EmailMessage

from mailer import creator


def spool_email_file(filename):
    with open(
            filename,
            "r",
            encoding="utf-8",
    ) as fd:
        data = json.load(fd)

    if "email" not in data or "message" not in data["email"]:
        log(f"ERROR: no message type specified")
        return False

    which_message = data["email"]["message"]
    if not os.path.isfile(f"{creator.TEMPLATE_DIR}/{which_message}.txt"):
        log(f"Template file {creator.TEMPLATE_DIR}/{which_message}.txt not found")
        return False

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{os.environ['BASE']}/emails"))
    template = environment.get_template(which_message + ".txt")

    data["policy"] = policy.policy_defaults
    data["policy"].update(policy.this_policy.data())

    content = template.render(**data)
    header = {}
    for line in content.split("\n"):
        if line == "":
            break
        hdr = line.split(":")
        tag = hdr[0].lower()
        if tag in header:
            if isinstance(header[tag], list):
                header[tag].append(hdr[1].strip())
            else:
                header[tag] = [hdr[1].strip(), header[tag]]
        else:
            header[hdr[0].lower()] = hdr[1].strip()

    content = content[content.find("\n\n") + 2:]

    if "to" not in header and "user" in data:
        header["to"] = data["user"]["email"]

    if isinstance(header["to"], str):
        header["to"] = [header["to"]]

    if "from" not in header:
        header["from"] = f"policy.this_policy.policy('policy.name_sender') <policy.this_policy.policy('email_return')>"

    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = header["subject"]
    msg['From'] = header["from"]
    msg['To'] = header["to"]

    smtp_from_addr = policy.this_policy.policy("email_return")
    if "x-env-from" in header:
        from_addr = header["x-env-from"]

    log(f"Emailing: {data['email']['message']} to {header['to']}")

    with smtplib.SMTP("127.0.0.1", 25) as smtp_cnx:
        smtp_cnx.send_message(msg, smtp_from_addr, header["to"])
        smtp_cnx.quit()

    return True


def process_emails_waiting():
    for file in os.listdir(creator.SPOOL_BASE):
        path = os.path.join(creator.SPOOL_BASE, file)
        if os.path.isfile(path) and spool_email_file(path):
            os.remove(path)
        else:
            os.replace(path, os.path.join(creator.ERROR_BASE, file))


def run_server():
    log("SMTP SPOOLER RUNNING")
    signal_mtime = None
    while True:
        new_mtime = os.path.getmtime(creator.SPOOL_BASE)
        if new_mtime == signal_mtime:
            time.sleep(3)
        else:
            process_emails_waiting()
            signal_mtime = new_mtime


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SMTP Spooler')
    parser.add_argument("-D", '--debug', action="store_true")
    args = parser.parse_args()
    log_init(with_debug=args.debug)

    sql.connect("engine")
    registry.start_up()
    run_server()
