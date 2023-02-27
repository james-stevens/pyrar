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

from librar.mysql import sql_server as sql
from librar import registry
from librar import policy
from librar.log import log, debug, init as log_init

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mailer import spool_email

DO_NOT_INCLUDE_TAGS = {"X-Env-From", "BCC"}
MULTILINE_TAGS = {"To", "CC", "BCC"}


def spool_email_file(filename, server=None):
    with open(
            filename,
            "r",
            encoding="utf-8",
    ) as fd:
        data = json.load(fd)

    if "email" not in data or "message" not in data["email"]:
        log(f"ERROR: no message type specified")
        return False, None

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
        return False, None

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{os.environ['BASE']}/emails"))
    template = environment.get_template(merge_file)

    data["policy"] = policy.policy_defaults
    data["policy"].update(policy.this_policy.data())

    content = template.render(**data)
    header = {}

    lines = [line.rstrip() for line in content.split("\n")]
    msg = MIMEMultipart('alternative')

    while (len(lines) and len(lines[0]) and (colon := lines[0].find(":")) > 0 and (space := lines[0].find(" ")) > 0
           and space > colon):

        tag = lines[0][:colon]
        rest = lines[0][colon + 2:]

        if tag in header and len(header[tag]) > 0 and tag in MULTILINE_TAGS:
            header[tag] += "," + rest
        else:
            header[tag] = rest

        del lines[0]

    if len(lines[0].rstrip()) == 0:
        del lines[0]

    if "To" not in header and "user" in data:
        header["To"] = data["user"]["email"]

    del header["From"]
    if "From" not in header:
        name = policy.this_policy.policy("name_sender")
        if name is None:
            name = policy.this_policy.policy("business_name")
        email = policy.this_policy.policy("email_return")
        header["From"] = f"{name} <{email}>"

    for tag in header:
        if tag not in DO_NOT_INCLUDE_TAGS:
            msg[tag] = header[tag]

    if is_html:
        msg.attach(MIMEText("\n".join(lines), 'html'))
    else:
        msg.attach(MIMEText("\n".join(lines), 'plain'))

    smtp_from_addr = policy.this_policy.policy("email_return")
    if "X-Env-From" in header:
        from_addr = header["X-Env-From"]

    all_rcpt = ""
    for hdr_tag in MULTILINE_TAGS:
        if hdr_tag in header and len(header[hdr_tag]) > 0:
            all_rcpt += "," + header[hdr_tag]
    all_rcpt = all_rcpt[1:]

    log(f"Emailing: {data['email']['message']} to {all_rcpt}")

    if server is None:
        server = policy.this_policy.policy("smtp_server")
    if server is None:
        server = "127.0.0.1"

    with smtplib.SMTP(server, 25) as smtp_cnx:
        smtp_cnx.sendmail(smtp_from_addr, all_rcpt.split(","), msg.as_string())
        smtp_cnx.quit()

    return True, data


def process_emails_waiting(server=None):
    for file in os.listdir(spool_email.SPOOL_BASE):
        path = os.path.join(spool_email.SPOOL_BASE, file)
        if not os.path.isfile(path):
            continue

        records = None
        try:
            ok, records = spool_email_file(path, server)
        except Exception as e:
            log(f"ERROR: Exception running spool_email_file '{path}' - {type(e)}:{str(e)}")
            ok = False

        if ok:
            if records is not None:
                spool_email.event_log("Delivered", records)
            os.remove(path)
        else:
            log(f"ERROR: Failed to process email '{path}'")
            os.replace(path, os.path.join(misc.make_year_month_day_dir(spool_email.ERROR_BASE), file))


def run_server():
    log("SMTP SPOOLER RUNNING")
    signal_mtime = None
    while True:
        new_mtime = os.path.getmtime(spool_email.SPOOL_BASE)
        if new_mtime == signal_mtime:
            registry.tld_lib.check_for_new_files()
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
