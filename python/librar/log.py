#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import syslog
import inspect
import datetime

done_init = False

hold_debug = False
hold_with_logging = True


def debug(line, where=None):
    if where is None:
        where = inspect.stack()[1]
    if hold_debug:
        log("[DEUBG] " + line, where)


def log(line, where=None):
    if where is None:
        where = inspect.stack()[1]
    txt = ""
    if where is not None:
        fname = where.filename.split("/")[-1].split(".")[0]
        txt = f"[{fname}:{str(where.lineno)}/{where.function}]"
    if hold_debug:
        now = datetime.datetime.now()
        now_txt = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{now_txt} SYSLOG{txt} {line}")
    else:
        if not done_init:
            init()
        if hold_with_logging:
            syslog.syslog(txt + " " + line)


def init(facility=syslog.LOG_LOCAL6, with_debug=False, with_logging=True):
    global hold_debug
    global hold_with_logging
    syslog.openlog(logoption=syslog.LOG_PID, facility=facility)
    hold_with_logging = with_logging
    hold_debug = with_debug
    done_init = True
