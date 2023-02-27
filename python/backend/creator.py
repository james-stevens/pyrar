#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" run job requests queued in table `backend` """

from librar import sigprocs
from librar.mysql import sql_server as sql


def make_backend_job(job_type, dom_db, num_years=None, authcode=None):
    backend_db = {
        "domain_id": dom_db["domain_id"],
        "user_id": dom_db["user_id"],
        "num_years": num_years,
        "authcode": authcode,
        "job_type": job_type,
        "failures": 0,
        "execute_dt": misc.now(),
        "created_dt": None,
        "amended_dt": None
    }

    ok = sql.sql_insert("backend", backend_db)
    sigprocs.signal_service("backend")
    return ok
