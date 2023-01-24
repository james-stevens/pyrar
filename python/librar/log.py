#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import syslog
import inspect
import datetime

done_init = False

hold_debug = False
hold_with_logging = True

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
    if hold_debug:
        log("[DEUBG] " + line, where)


def log(line, where=None, default_level=syslog.LOG_NOTICE):
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
            if isinstance(default_level, str):
                default_level = severity_options[default_level]
            syslog.syslog(txt + " " + line)


def init(facility="local0", with_debug=False, with_logging=True, default_level=syslog.LOG_NOTICE):
    global hold_debug
    global hold_with_logging
    global done_init

    if isinstance(facility, str):
        facility = facility_options[facility]

    syslog.openlog(logoption=syslog.LOG_PID, facility=facility)
    hold_with_logging = with_logging
    hold_debug = with_debug
    done_init = True


if __name__ == "__main__":
    init("local5", with_debug=True)
    debug("Hello")
