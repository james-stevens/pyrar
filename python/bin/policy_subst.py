#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" substitute policy values in all files in `${BASE}/policy_subst` """

import os
import jinja2

from librar.policy import this_policy as policy
from librar import fileloader
from librar import static

SRC_DIR = f"{os.environ['BASE']}/policy_subst/"
DEST_DIR = "/run/policy_subst/"

merge_data = {"logins": fileloader.load_file_json(static.LOGINS_FILE), "policy": policy.data()}
with open("/run/pdns_api_key", "r", encoding="UTF-8") as fd:
    merge_data["api_key"] = fd.readline().strip()

if not os.path.isdir(DEST_DIR):
    os.mkdir(DEST_DIR, mode=0o755)

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(SRC_DIR))
for file in os.listdir(SRC_DIR):
    if os.path.isfile(os.path.join(SRC_DIR, file)):
        dst_path = os.path.join(DEST_DIR, file)
        template = environment.get_template(file)
        content = template.render(**merge_data)
        with open(dst_path, "w", encoding="UTF-8") as fd:
            fd.write(content)
