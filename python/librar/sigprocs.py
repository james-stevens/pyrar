#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

import os
import sys
import time

from librar import fileloader


def signal_filename(sig_name):
    return f"{os.environ['BASE']}/storage/shared/signals/{sig_name}.sig"


def signal_service(sig_name):
    file = signal_filename(sig_name)
    now = int(time.time())
    if not os.path.isfile(file):
        remake_sig_file(file)
    file_mtime = os.path.getmtime(file)
    if file_mtime == now:
        now += 1
    os.utime(file, (now, now))


def remake_sig_file(file):
    print("REMAKE", file)
    try:
        os.remove(file)
    except FileNotFoundError:
        pass
    with open(file, "w") as file_des:
        pass
    return fileloader.have_newer(None, file)


def signal_wait(sig_name, prev_mtime=None, loop_time=1, max_wait=30):
    file = signal_filename(sig_name)
    if not os.path.isfile(file):
        remake_sig_file(file)

    try:
        loop_mtime = fileloader.have_newer(prev_mtime, file)
    except PermissionError:
        loop_mtime = remake_sig_file(file)

    if loop_mtime is None:
        loop_mtime = prev_mtime

    total_waited = 0
    while True:
        try:
            next_mtime = fileloader.have_newer(loop_mtime, file)
        except PermissionError:
            next_mtime = remake_sig_file(file)

        if next_mtime is not None:
            break

        time.sleep(loop_time)
        total_waited += loop_time
        if total_waited > max_wait:
            return loop_mtime

    return next_mtime


if __name__ == "__main__":
    if len(sys.argv) > 1:
        signal_service(sys.argv[1])
        sys.exit(0)

    this_mtime = None
    while True:
        this_mtime = signal_wait("backend", prev_mtime=this_mtime)
        if this_mtime is None:
            break
        print(">>>> PING", this_mtime)
