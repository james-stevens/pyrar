#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import lib.log as log


def load_file_json(filename):
    log.log(f"Reloading file '{filename}'")
    try:
        with open(filename, "r", encoding='UTF-8') as file_fd:
            if file_fd.readable():
                json = json.load(file_fd)
        return json
    except Exception as err:
        log.log(f"{filename} : {str(err)}")

    return None


def have_newer(mtime, file_name):
    if not os.path.isfile(file_name) or not os.access(file_name, os.R_OK):
        return None

    if (new_time := os.path.getmtime(file_name)) <= mtime:
        return None

    return new_time


class FileLoader:
    def __init__(self, filename):
        self.filename = filename
        self.last_mtime = 0
        self.check_for_newer()

    def check_for_new(self):
        if (new_time := have_newer(self.last_mtime, self.filename)) is None:
            return False
        if (json := load_file_json(self.filename)) is not None:
            self.json = json
            self.last_mtime = new_time
            return True
        return False

    def data(self):
        self.check_for_new()
        return self.json

    def check(self):
        ret = self.check_for_new()
        return self.json, ret
