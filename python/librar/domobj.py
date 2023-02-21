#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" define class for handling domains """

import sys

from librar import mysql as sql
from librar import registry
from librar import static
from librar import validate
from librar import log
from librar.policy import this_policy as policy


class Domain:
    """ domain handler """
    def __init__(self):
        self.name = None
        self.registry = None
        self.tld = None
        self.tld_rec = None
        self.dom_db = None
        self.locks = None
        self.permitted_locks = None
        self.locks = None

    def set_by_id(self, domain_id=None, user_id=None):
        if domain_id is None or not isinstance(domain_id, int):
            return False, "Imvalid domain id"
        where = {"domain_id": domain_id}
        if user_id is not None:
            where["user_id"] = user_id

        ok, self.dom_db = sql.sql_select_one("domains", where)
        if not ok:
            return False, "Domain not found"
        self.set_locks()
        return self.set_name(self.dom_db["name"])

    def set_name(self, name):
        """ check the name is valid & find its registry """
        name = name.lower()
        if not validate.is_valid_fqdn(name):
            return False, "Invalid domain name"
        if (idx := name.find(".")) < 0:
            return False, "Invalid domain name"
        tld = name[idx + 1:]
        if tld not in registry.tld_lib.zone_data:
            return False, "TLD not supported"

        self.tld = tld
        self.tld_rec = registry.tld_lib.zone_data[self.tld]
        self.registry = self.tld_rec["reg_data"]
        self.permitted_locks = static.CLIENT_DOM_FLAGS

        if "locks" in self.registry:
            self.permitted_locks = self.registry["locks"]
        self.name = name
        return True, None

    def load_name(self, name, user_id=None):
        if not (reply := self.set_name(name))[0]:
            return False, reply[1]
        return self.load_record(user_id)

    def load_record(self, user_id=None):
        """ load the domain from the database """
        if self.name is None or self.registry is None or self.tld is None:
            return False, "Use `set_name` before `load_record`"
        self.dom_db = None
        where = {"name": self.name}
        if user_id is not None:
            where["user_id"] = user_id

        ok, dom_db = sql.sql_select_one("domains", where)
        if not ok:
            return False, "Domain failed to load"
        return self.set_locks()

    def set_locks(self):
        self.locks = {}
        if self.dom_db is not None and sql.has_data(self.dom_db, "client_locks"):
            self.locks = {lock: True for lock in self.dom_db["client_locks"].split(",")}
        return True, None

    def valid_expiry_limit(self, num_years):
        renew_limit = policy.policy("renew_limit")
        if "renew_limit" in self.tld_rec:
            renew_limit = self.tld_rec["renew_limit"]
        elif "renew_limit" in self.registry:
            renew_limit = self.registry["renew_limit"]

        if self.dom_db is None and not self.load_record():
            return num_years <= renew_limit

        if not sql.has_data(self.dom_db, ["name", "expiry_dt"]):
            return num_years <= renew_limit

        limit_dt = sql.date_add(sql.now(), years=renew_limit)
        new_expiry_dt = sql.date_add(self.dom_db["expiry_dt"], years=num_years)
        return new_expiry_dt <= limit_dt


class DomainList:
    """ validate domain list requested by users """
    def __init__(self):
        self.domobjs = None
        self.registry = None
        self.currency = None
        self.xmlns = None
        self.client = None

    def set_list(self, dom_list):
        if isinstance(dom_list, str):
            if dom_list.find(",") >= 0:
                ok, reply = self.process_list(dom_list.split(","))
            else:
                ok, reply = self.process_list([dom_list])
        elif isinstance(dom_list, list):
            if len(dom_list) <= 0:
                return False, "Empty list"
            ok, reply = self.process_list(dom_list)
        else:
            ok = False
            reply = "Unsupported data sent"

        if not ok:
            return False, reply

        self.currency = self.registry["currency"] if "currency" in self.registry else policy.policy("currency")
        if self.registry["type"] == "epp":
            self.xmlns = registry.make_xmlns(self.registry)
            self.client = registry.tld_lib.clients[self.registry["name"]]
        return True, True

    def process_list(self, dom_list):
        self.domobjs = {}
        for name in dom_list:
            this_domobj = Domain()
            ok, reply = this_domobj.set_name(name)
            if not ok:
                return False, reply
            if self.registry is None:
                self.registry = this_domobj.registry
            else:
                if self.registry["name"] != this_domobj.registry["name"]:
                    return False, "ERROR: Split registry request"
            self.domobjs[this_domobj.name] = this_domobj
        return True, None

    def load_all(self):
        if self.domobjs is None:
            return False, "Use `set_list` before `load_all`"

        ok, dom_dbs = sql.sql_select("domains",{"name": [dom.name for __, dom in self.domobjs.items()]},limit=len(self.domobjs))
        if not ok or not dom_dbs:
            return False, "Failed to load domains from database"

        domdb_by_name = {dom_db["name"]: dom_db for dom_db in dom_dbs}
        for __, dom in self.domobjs.items():
            dom.dom_db = None
            if dom.name in domdb_by_name:
                dom.dom_db = domdb_by_name[dom.name]
                dom.set_locks()

        return True, None


if __name__ == "__main__":
    log.init(with_debug=True)
    sql.connect("webui")
    registry.start_up()
    # my_dom = Domain()
    # print("ONE:DOMS>>>", my_dom.set_by_id(int(sys.argv[1])),my_dom.__dict__)
    # print("ONE:DOMS>>>", my_dom.load_name(sys.argv[1]), my_dom.registry)
    # sys.exit(0)
    # print("LOADDB>>>", my_dom.load_record(), my_dom.dom_db)
    # print("EXP>>>>", my_dom.valid_expiry_limit(5), my_dom.valid_expiry_limit(15))
    # print("LOCKS>>>>", my_dom.locks)

    my_doms = DomainList()
    if not (tst_reply := my_doms.set_list(sys.argv[1:]))[0]:
        print(tst_reply)
        sys.exit(1)
    print("LIST>>>", tst_reply[1])
    print("load all", my_doms.load_all())
    for d, domobj in my_doms.domobjs.items():
        print(d, domobj.name, domobj.dom_db["name"] if domobj.dom_db is not None else "NOPE", domobj.locks)
