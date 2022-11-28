#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import syslog

done_init = False

hold_debug = False
hold_with_logging = True


def debug(line, where):
    if hold_debug:
        log("[DEUBG] " + line, where)


def log(line, where=None):
    if hold_debug:
        txt = ""
        if where is not None:
            txt = "[" + where.filename.split("/")[-1] + ":" + str(
                where.lineno) + "]"
        print(f">>>SYSLOG{txt} {line}")
    else:
        txt = ""
        if where is not None:
            txt = "[" + where.filename.split("/")[-1] + ":" + str(
                where.lineno) + "]"
        if not done_init:
            init()
        if hold_with_logging:
            syslog.syslog(txt + line)


def init(facility=syslog.LOG_LOCAL6, debug=False, with_logging=True):
    global hold_debug
    global hold_with_logging
    syslog.openlog(logoption=syslog.LOG_PID, facility=facility)
    hold_with_logging = with_logging
    hold_debug = debug
    done_init = True
