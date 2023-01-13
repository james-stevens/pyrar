#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" display JSON files as flat text For processing in shall scripts """

import sys
import json

from librar import flatten

for file in sys.argv[1:]:
    with open(file, "r", encoding='UTF-8') as fd:
        for idx, val in flatten.flatten(json.load(fd)).items():
            print(f"{idx}={val}")
