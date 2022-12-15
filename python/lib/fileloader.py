#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
from inspect import currentframe as czz, getframeinfo as gzz
from lib.log import log, init as log_init


def load_file_json(filename):
    log(f"Reloading file '{filename}'", gzz(czz()))
    try:
        with open(filename, "r", encoding='UTF-8') as file_fd:
            if file_fd.readable():
                data = json.load(file_fd)
                return data
    except Exception as err:
        log(f"load_file_json: {filename} : {str(err)}", gzz(czz()))

    return None


def have_newer(mtime, file_name):
    if not os.path.isfile(file_name) or not os.access(file_name, os.R_OK):
        raise PermissionError

    new_time = os.path.getmtime(file_name)
    if mtime is None:
        return new_time

    if new_time == mtime:
        return None

    return new_time


class FileLoader:
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
    log_init(with_debug=True)
    file = FileLoader(f"{os.environ['BASE']}/etc/logins.json")
    print(json.dumps(file.json, indent=4))
