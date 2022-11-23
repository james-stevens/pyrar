#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import os
import lib.fileloader as fileloader
import lib.log as log

WEBUI_POLICY = os.environ["BASE"] + "/etc/policy.json"


class Policy:
    def __init__(self, var=None):
        self.file = None

        self.file = fileloader.FileLoader(WEBUI_POLICY)
        if var is not None:
            log.with_logging = self.policy(var, True)

    def policy(self, name, val=None):
        our_policy = self.file.data()
        if name in our_policy:
            return our_policy[name]
        return val

    def data(self):
        return self.file.data()


if __name__ == "__main__":
    mine = Policy("log_python_code")
    print(">>>TEST>>>", mine.policy("business_name", "Unk"))
    print(">>>TEST>>>", mine.policy("log_python_code", "Unk"))
