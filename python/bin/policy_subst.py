#! /usr/bin/python3

import os
import re
import sys

from lib.policy import this_policy as policy
from lib import fileloader

SRC_DIR = f"{os.environ['BASE']}/policy_subst/"
DEST_DIR="/run/policy_subst/"

LOGINS_JSON=f"{os.environ['BASE']}/etc/logins.json"
logins = fileloader.load_file_json(LOGINS_JSON)

with open("/run/pdns_api_key","r") as fd:
    policy.add_policy(f"api_key",fd.readline().strip())

policy_re = re.compile(r'{[a-zA-Z0-9_\.]+(,.+)?}')


for registry,this_login in logins.items():
    for login_prop in this_login:
        policy.add_policy(f"logins.{registry}.{login_prop}",this_login[login_prop])


def subst_file(filename):
    with open(SRC_DIR+filename,"r") as in_fd:
        with open(DEST_DIR+filename,"w") as out_fd:
            for line in in_fd.readlines():
                while (res := policy_re.search(line)) is not None:
                    match_chars = res.span()
                    match_str = res.group()[1:-1]
                    if match_str.find(",") >= 0:
                        split_comma = match_str.split(",")
                        pol_val = policy.policy(split_comma[0],split_comma[1])
                        line = line[:match_chars[0]] + pol_val + line[match_chars[1]:]
                    else:
                        if (pol_val := policy.policy(match_str,None)) is not None:
                            line = line[:match_chars[0]] + pol_val + line[match_chars[1]:]
                        else:
                            line=""
                out_fd.write(line)


if not os.path.isdir(DEST_DIR):
    os.mkdir(DEST_DIR, mode = 0o755)

for filename in os.listdir(f"{os.environ['BASE']}/policy_subst"):
    subst_file(filename)
