#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from os.path import dirname, basename, isfile, join
import glob

modules = glob.glob(join(dirname(__file__), "[a-z]*.py"))
__all__ = [basename(f)[:-3] for f in modules if isfile(f)]
