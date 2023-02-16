#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles plug-in modules for domain interfaces needed by the UI """

from webui import pay_handler
# pylint: disable=unused-wildcard-import, wildcard-import
from webui.pay_plugins import *


def main():
    ok, reply = pay_handler.run("paypal_single","single")(10450)
    print(reply)


if __name__ == "__main__":
    main()
