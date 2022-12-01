#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" XML library """


def xmlcode(reply):
    """ return EPP return code from {reply} """
    if (reply is not None) and (isinstance(reply,dict)) and ("result" in reply) and ("@code" in reply["result"]):
        return int(reply["result"]["@code"])
    return 9999
