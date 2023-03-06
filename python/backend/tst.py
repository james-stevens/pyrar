#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import json

from librar.mysql import sql_server as sql
from librar import registry, log, domobj
from backend import libback

log.init(with_debug=True)
sql.connect("engine")
registry.start_up()
my_domlist = domobj.DomainList()
my_domlist.set_list(",".join(sys.argv[1:]))
print(json.dumps(libback.get_prices(my_domlist, 1, ["create", "renew"]), indent=3))
