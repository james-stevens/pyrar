#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" entry point for running web/ui rest/api - called by start-yp shell scr """

from webui.run_webui import application

if __name__ == "__main__":
    application.run()
