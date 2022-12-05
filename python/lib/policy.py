#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
import os
import lib.fileloader as fileloader
import lib.log as log

WEBUI_POLICY = os.environ["BASE"] + "/etc/policy.json"


class Policy:
    def __init__(self):
        self.file = None
        self.file = fileloader.FileLoader(WEBUI_POLICY)

    def policy(self, name, def_val=None):
        our_policy = self.file.data()
        if name in our_policy:
            return our_policy[name]
        return def_val

    def data(self):
        return self.file.data()


this_policy = Policy()

if __name__ == "__main__":
    print(">>>TEST>>>", this_policy.policy("business_name", "Unk"))
    print(">>>TEST>>>", this_policy.policy("log_python_code", "Unk"))
