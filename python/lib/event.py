#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from inspect import currentframe, getframeinfo

def event(desc,frameinfo):
    print(">>>>>",desc,frameinfo)
