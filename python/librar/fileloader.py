#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" load / reload JSON config files """

import sys
import os
import json
import inspect
import syslog


def load_file_json(filename):
    where = inspect.stack()[1]
    fname = where.filename.split("/")[-1].split(".")[0]
    txt = f"[{fname}:{str(where.lineno)}/{where.function}]"
    syslog.syslog(syslog.LOG_NOTICE, f"{txt} -> Reloading file '{filename}'")
    try:
        with open(filename, "r", encoding='UTF-8') as file_fd:
            if file_fd.readable():
                data = json.load(file_fd)
                return data
    except (ValueError, IOError) as err:
        syslog.syslog(syslog.LOG_ERR, f"{txt} -> load_file_json: {filename} : {str(err)}")

    return None


def have_newer(mtime, file_name):
    if not os.path.isfile(file_name) or not os.access(file_name, os.R_OK):
        raise PermissionError(f"'{file_name}' not found or not readable")

    new_time = os.path.getmtime(file_name)
    if mtime is None:
        return new_time

    if new_time == mtime:
        return None

    return new_time


class FileLoader:
    """ load & update a json file """
    def __init__(self, filename):
        self.filename = filename
        self.last_mtime = 0
        self.json = None
        self.check_for_new()

    def check_for_new(self):
        if (new_time := have_newer(self.last_mtime, self.filename)) is None:
            return False
        if (data := load_file_json(self.filename)) is not None:
            self.json = data
            self.last_mtime = new_time
            return True
        return False

    def data(self):
        self.check_for_new()
        return self.json

    def check(self):
        return self.check_for_new()


if __name__ == "__main__":
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL0)
    file = FileLoader(sys.argv[1])
    print(json.dumps(file.json, indent=4))
