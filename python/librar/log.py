#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import syslog
import inspect
import datetime

done_init = False

hold_debug = False
hold_with_logging = True

# Syslog codes from /usr/lib/python3.10/logging/handlers.py
# priorities (these are ordered)
LOG_EMERG = 0  # system is unusable
LOG_ALERT = 1  # action must be taken immediately
LOG_CRIT = 2  # critical conditions
LOG_ERR = 3  # error conditions
LOG_WARNING = 4  # warning conditions
LOG_NOTICE = 5  # normal but significant condition
LOG_INFO = 6  # informational
LOG_DEBUG = 7  # debug-level messages

# facility codes
LOG_KERN = 0  # kernel messages
LOG_USER = 1  # random user-level messages
LOG_MAIL = 2  # mail system
LOG_DAEMON = 3  # system daemons
LOG_AUTH = 4  # security/authorization messages
LOG_SYSLOG = 5  # messages generated internally by syslogd
LOG_LPR = 6  # line printer subsystem
LOG_NEWS = 7  # network news subsystem
LOG_UUCP = 8  # UUCP subsystem
LOG_CRON = 9  # clock daemon
LOG_AUTHPRIV = 10  # security/authorization messages (private)
LOG_FTP = 11  # FTP daemon
LOG_NTP = 12  # NTP subsystem
LOG_SECURITY = 13  # Log audit
LOG_CONSOLE = 14  # Log alert
LOG_SOLCRON = 15  # Scheduling daemon (Solaris)

# other codes through 15 reserved for system use
LOG_LOCAL0 = 16  # reserved for local use
LOG_LOCAL1 = 17  # reserved for local use
LOG_LOCAL2 = 18  # reserved for local use
LOG_LOCAL3 = 19  # reserved for local use
LOG_LOCAL4 = 20  # reserved for local use
LOG_LOCAL5 = 21  # reserved for local use
LOG_LOCAL6 = 22  # reserved for local use
LOG_LOCAL7 = 23  # reserved for local use

facility_names = {
    "auth": LOG_AUTH,
    "authpriv": LOG_AUTHPRIV,
    "console": LOG_CONSOLE,
    "cron": LOG_CRON,
    "daemon": LOG_DAEMON,
    "ftp": LOG_FTP,
    "kern": LOG_KERN,
    "lpr": LOG_LPR,
    "mail": LOG_MAIL,
    "news": LOG_NEWS,
    "ntp": LOG_NTP,
    "security": LOG_SECURITY,
    "solaris-cron": LOG_SOLCRON,
    "syslog": LOG_SYSLOG,
    "user": LOG_USER,
    "uucp": LOG_UUCP,
    "local0": LOG_LOCAL0,
    "local1": LOG_LOCAL1,
    "local2": LOG_LOCAL2,
    "local3": LOG_LOCAL3,
    "local4": LOG_LOCAL4,
    "local5": LOG_LOCAL5,
    "local6": LOG_LOCAL6,
    "local7": LOG_LOCAL7,
}


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


def init(facility="local0", with_debug=False, with_logging=True, default_level=LOG_NOTICE):
    global hold_debug
    global hold_with_logging
    global done_init

    if isinstance(facility, str):
        facility = (facility_names[facility] << 3) + default_level

    syslog.openlog(logoption=syslog.LOG_PID, facility=facility)
    hold_with_logging = with_logging
    hold_debug = with_debug
    done_init = True


if __name__ == "__main__":
    init("local5", with_debug=True)
    debug("Hello")
