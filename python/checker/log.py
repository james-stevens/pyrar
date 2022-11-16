#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import syslog

debug = False
done_init = False

def log(line):
    if debug:
        print(">>>>>>",line)
    else:
        if not done_init:
            init()
        syslog.syslog(line)

def init(facility=syslog.LOG_LOCAL6):
    syslog.openlog(logoption=syslog.LOG_PID, facility=facility)
    done_init = True
