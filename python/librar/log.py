#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions for sys-logging """

import sys
import syslog
import inspect
import datetime

from librar.policy import this_policy as policy

DONE_INIT = False

HOLD_DEBUG = False
HOLD_WITH_LOGGING = True

facility_options = {
    "kern": syslog.LOG_KERN,
    "kernel": syslog.LOG_KERN,
    "user": syslog.LOG_USER,
    "mail": syslog.LOG_MAIL,
    "daemon": syslog.LOG_DAEMON,
    "auth": syslog.LOG_AUTH,
    "syslog": syslog.LOG_SYSLOG,
    "lpr": syslog.LOG_LPR,
    "news": syslog.LOG_NEWS,
    "uucp": syslog.LOG_UUCP,
    "cron": syslog.LOG_CRON,
    "authpriv": syslog.LOG_AUTHPRIV,
    "local0": syslog.LOG_LOCAL0,
    "local1": syslog.LOG_LOCAL1,
    "local2": syslog.LOG_LOCAL2,
    "local3": syslog.LOG_LOCAL3,
    "local4": syslog.LOG_LOCAL4,
    "local5": syslog.LOG_LOCAL5,
    "local6": syslog.LOG_LOCAL6,
    "local7": syslog.LOG_LOCAL7
}

severity_options = {
    "emerg": syslog.LOG_EMERG,
    "emergency": syslog.LOG_EMERG,
    "alert": syslog.LOG_ALERT,
    "crit": syslog.LOG_CRIT,
    "critical": syslog.LOG_CRIT,
    "err": syslog.LOG_ERR,
    "error": syslog.LOG_ERR,
    "warning": syslog.LOG_WARNING,
    "notice": syslog.LOG_NOTICE,
    "info": syslog.LOG_INFO,
    "information": syslog.LOG_INFO,
    "debug": syslog.LOG_DEBUG
}


def debug(line, where=None):
    if where is None:
        where = inspect.stack()[1]
    if HOLD_DEBUG:
        log("[DEUBG] " + line, where)


def log(line, where=None, default_level=syslog.LOG_NOTICE):
    if where is None:
        where = inspect.stack()[1]
    txt = ""
    if where is not None:
        fname = where.filename.split("/")[-1].split(".")[0]
        txt = f"[{fname}:{str(where.lineno)}/{where.function}]"
    if HOLD_DEBUG:
        now = datetime.datetime.now()
        now_txt = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{now_txt} SYSLOG{txt} {line}")
    else:
        if not DONE_INIT:
            init()
        if HOLD_WITH_LOGGING:
            if isinstance(default_level, str):
                default_level = severity_options[default_level]
            syslog.syslog(default_level, txt + " " + line)


def check_off(this_facility, also_check_none=False):
    global HOLD_WITH_LOGGING
    global DONE_INIT
    if this_facility in ["None","Off"] or (also_check_none and this_facility is None):
        HOLD_WITH_LOGGING = False
        DONE_INIT = True
        return True
    return False


def init(inp_facility=None, with_debug=False, with_logging=True):
    global HOLD_DEBUG
    global HOLD_WITH_LOGGING
    global DONE_INIT

    if check_off(inp_facility):
        return

    if inp_facility in facility_options:
        this_facility = facility_options[inp_facility]
    else:
        if (this_facility := policy.policy(inp_facility)) is None:
            this_facility = policy.policy("logging_default")

    if check_off(this_facility, True):
        return

    if this_facility in facility_options:
        this_facility = facility_options[this_facility]

    syslog.openlog(logoption=syslog.LOG_PID, facility=this_facility)
    HOLD_WITH_LOGGING = with_logging
    HOLD_DEBUG = with_debug
    DONE_INIT = True


if __name__ == "__main__":
    init(sys.argv[1], with_debug=True)
    debug("Hello")
