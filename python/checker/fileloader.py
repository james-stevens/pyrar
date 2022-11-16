#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import json
import log


def have_newer(mtime, file_name):
    if not os.path.isfile(file_name) or not os.access(file_name, os.R_OK):
        return None

    if (new_time := os.path.getmtime(file_name)) <= mtime:
        return None

    return new_time


class FileLoader:
    def __init__(self,filename):
        self.filename = filename
        self.last_mtime = 0;

    def check_for_new(self):
        if (new_time := have_newer(self.last_mtime,self.filename)) is None:
            return False

        log.log(f"NORMAL: Reloading file '{self.filename}'")
        try:
            with open(self.filename, "r", encoding='UTF-8') as file_fd:
                if file_fd.readable():
                    self.json = json.load(file_fd)
            self.last_mtime = new_time
            return True
        except Exception as err:
            dolog(f"{self.zone_file} : {str(err)}")

        return False

    def data(self):
        ret = self.check_for_new();
        return self.json, ret
