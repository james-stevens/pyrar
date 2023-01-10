#! /usr/bin/python3

import os
import sys
import json
import jinja2

from librar import policy
from librar import fileloader
from librar import misc

SRC_DIR = f"{os.environ['BASE']}/policy_subst/"
DEST_DIR = "/run/policy_subst/"

merge_data = { "logins":fileloader.load_file_json(misc.LOGINS_JSON) }
with open("/run/pdns_api_key", "r") as fd:
    merge_data["api_key"] = fd.readline().strip()

merge_data["policy"] = policy.policy_defaults
merge_data["policy"].update(policy.this_policy.data())

if not os.path.isdir(DEST_DIR):
    os.mkdir(DEST_DIR, mode=0o755)

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(SRC_DIR))
for file in os.listdir(SRC_DIR):
    if os.path.isfile(os.path.join(SRC_DIR,file)):
        dst_path = os.path.join(DEST_DIR, file)
        template = environment.get_template(file)
        content = template.render(**merge_data)
        with open(dst_path,"w") as fd:
            fd.write(content)
