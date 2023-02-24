#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" handles payment.json file to avoid circular references """

from librar import static
from librar import fileloader

payment_file = fileloader.FileLoader(static.PAYMENT_FILE)
