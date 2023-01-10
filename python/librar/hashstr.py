#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import sys
import re
import hashlib
import base64


def hash_confirm(src_string):
    hsh = hashlib.sha256()
    hsh.update(src_string.encode("utf-8"))
    return re.sub("[+/.=]", "", base64.b64encode(hsh.digest()).decode("utf-8"))[:20]
