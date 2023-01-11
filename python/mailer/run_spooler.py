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

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mailer import spool_email

RCPT_TAGS = {"to": "To", "cc": "CC", "bcc": "BCC"}


def spool_email_file(filename, server=None):
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
    pfx = f"{spool_email.TEMPLATE_DIR}/{which_message}"
    merge_file = None
    is_html = False
    if os.path.isfile(f"{pfx}.txt"):
        merge_file = f"{which_message}.txt"
    elif os.path.isfile(f"{pfx}.html"):
        merge_file = f"{which_message}.html"
        is_html = True
    else:
        log(f"No merge message file found for '{which_message}'")
        return False

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{os.environ['BASE']}/emails"))
    template = environment.get_template(merge_file)

    data["policy"] = policy.policy_defaults
    data["policy"].update(policy.this_policy.data())

    content = template.render(**data)
    header = {}
    lines = [line.rstrip() for line in content.split("\n")]
    while len(lines) and lines[0] != "":
        colon = lines[0].find(":")
        space = lines[0].find(":")
        if colon < 0 or space < 0 or space < colon:
            break

        tag = lines[0][:colon].lower()
        rest = lines[0][colon + 2:]

        if tag in header:
            if isinstance(header[tag], list):
                header[tag].append(rest)
            else:
                header[tag] = [rest, header[tag]]
        else:
            header[tag] = rest
        del lines[0]

    if "to" not in header and "user" in data:
        header["to"] = data["user"]["email"]

    for hdr_tag in RCPT_TAGS:
        if hdr_tag in header and isinstance(header[hdr_tag], str):
            header[hdr_tag] = [header[hdr_tag]]

    if "from" not in header:
        header["from"] = f"policy.this_policy.policy('policy.name_sender') <policy.this_policy.policy('email_return')>"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = header["subject"]
    msg['From'] = header["from"]
    for hdr_tag in RCPT_TAGS:
        if hdr_tag in header:
            msg[RCPT_TAGS[hdr_tag]] = ",".join(header[hdr_tag])

    if is_html:
        msg.attach(MIMEText("\n".join(lines), 'html'))
    else:
        msg.attach(MIMEText("\n".join(lines), 'plain'))

    smtp_from_addr = policy.this_policy.policy("email_return")
    if "x-env-from" in header:
        from_addr = header["x-env-from"]

    log(f"Emailing: {data['email']['message']} to {header['to']}")

    all_rcpt = []
    for hdr_tag in RCPT_TAGS:
        if hdr_tag in header and len(header[hdr_tag]) > 0:
            all_rcpt.append(header[hdr_tag])

    if server is None:
        server = "127.0.0.1"

    with smtplib.SMTP(server, 25) as smtp_cnx:
        smtp_cnx.sendmail(smtp_from_addr, all_rcpt, msg.as_string())
        smtp_cnx.quit()

    return True


def process_emails_waiting(server=None):
    for file in os.listdir(spool_email.SPOOL_BASE):
        path = os.path.join(spool_email.SPOOL_BASE, file)
        if not os.path.isfile(path):
            continue

        try:
            ok = spool_email_file(path, server)
        except Exception as e:
            log(f"ERROR: Failed to email '{path}'")
            ok = False

        if ok:
            os.remove(path)
        else:
            log(f"ERROR: Failed to process email '{path}'")
            os.replace(path, os.path.join(spool_email.ERROR_BASE, file))


def run_server():
    log("SMTP SPOOLER RUNNING")
    signal_mtime = None
    while True:
        new_mtime = os.path.getmtime(spool_email.SPOOL_BASE)
        if new_mtime == signal_mtime:
            time.sleep(3)
        else:
            process_emails_waiting()
            signal_mtime = new_mtime


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SMTP Spooler')
    parser.add_argument("-D", '--debug', action="store_true")
    parser.add_argument("-S", '--server')
    args = parser.parse_args()
    log_init(with_debug=args.debug)

    sql.connect("engine")
    registry.start_up()

    if args.server:
        process_emails_waiting(args.server)
    else:
        run_server()
