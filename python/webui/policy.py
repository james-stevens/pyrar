#! /usr/bin/python3
#######################################################
#    (c) Copyright 2022-2022 - All Rights Reserved    #
#######################################################

import os
import fileloader
import log

WEBUI_POLICY = os.environ["BASE"] + "/etc/policy.json"

def policy(name,val=None):
    our_policy = policy_file.data()
    if name in our_policy:
        return our_policy[name]
    return val


def data():
	return policy_file.data()


policy_file = fileloader.FileLoader(WEBUI_POLICY)
log.with_logging = policy("log_python_req",True)

if __name__ == "__main__":
    print(">>>>>",policy("business_name","Unk"))
