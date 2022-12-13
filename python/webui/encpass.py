#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import bcrypt

print(sys.argv[1]+":"+bcrypt.hashpw(sys.argv[2].encode("utf-8"), bcrypt.gensalt()).decode("utf-8"))
