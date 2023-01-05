#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import jinja2
import datetime

from librar import mysql as sql
from librar import flat
from librar import registry
from librar import policy

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{os.environ['BASE']}/emails"))
template = environment.get_template("reminder.txt")

sql.connect("engine")
registry.start_up()

data = {}

now = datetime.datetime.now()
data["email"] = {
	"date": now.strftime('%a, %d %b %Y %T %z')
	}

data["policy"] = policy.policy_defaults
data["policy"].update(policy.this_policy.data())
__, data["user"] = sql.sql_select_one("users",{"email":"flip@flop.com"})
__, data["domain"] = sql.sql_select_one("domains",{"name":"pant.to.glass"})

content = template.render(**data)
print(content)
