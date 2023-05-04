#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" Refund a sale """

import sys

from librar import mysql, accounts
from librar.mysql import sql_server as sql


class Refund:
    def __init__(self):
        self.sale_db = None
        self.dom_db = None
        self.user_db = None
        self.trans_db = None
        self.refund_db = None

    def run_refund(self, sales_item_id):
        ok, reply = self.load_data(sales_item_id)
        if not ok:
            return False, reply

        ok, reply = self.create_refund_db()
        if not ok:
            return False, reply

        self.log_event()
        return self.save_refund()

    def load_data(self, sales_item_id):
        ok, self.sale_db = sql.sql_select_one("sales", {"sales_item_id": sales_item_id})
        if not ok:
            return False, "Sales record not found"

        if self.sale_db["been_refunded"]:
            return False, "Already been refunded"

        ok, rows = sql.sql_select("sales", {
            "domain_id": self.sale_db["domain_id"],
            "is_refund_of": None
        },
                                  order_by="sales_item_id desc",
                                  limit=1)
        if not ok or len(rows) != 1:
            return False, "Most recent sales record not found"

        if rows[0]["sales_item_id"] != self.sale_db["sales_item_id"]:
            return False, "Can only refund most recent sale"

        ok, self.dom_db = sql.sql_select_one("domains", {"domain_id": self.sale_db["domain_id"]})
        if not ok:
            return False, "Domain could not be found for that sale"

        if self.dom_db["user_id"] != self.sale_db["user_id"]:
            return False, "Domain has changed hands since that sale"

        ok, self.user_db = sql.sql_select_one("users", {"user_id": self.sale_db["user_id"]})
        if not ok:
            return False, "User record for that sale can't be found"

        ok, self.trans_db = sql.sql_select_one("transactions", {"transaction_id": self.sale_db["transaction_id"]})
        if not ok:
            return False, "Transaction record for that sale can't be found"

        return True, True

    def create_refund_db(self):
        self.refund_db = self.sale_db.copy()
        self.refund_db["sales_item_id"] = None
        self.refund_db["is_refund_of"] = self.sale_db["sales_item_id"]
        self.refund_db["sales_type"] = f"Refund:{self.sale_db['sales_type']}"
        self.refund_db["price_paid"] = self.refund_db["price_paid"]

        ok, refund_trans_id = accounts.apply_transaction(self.user_db["user_id"],
                                                         self.refund_db["price_paid"],
                                                         f"Refund: {self.trans_db['description']}",
                                                         as_admin=True)
        if not ok:
            return False, "Failed to refund account"

        self.refund_db["price_paid"] = self.refund_db["price_paid"] * -1
        self.refund_db["transaction_id"] = refund_trans_id
        return True, True

    def save_refund(self):
        ok, refund_row_id = sql.sql_insert("sales", self.refund_db)
        if not ok or not refund_row_id:
            return False, "Inserting refund failed"

        sql.sql_update_one("transactions", {"sales_item_id": refund_row_id},
                           {"transaction_id": self.refund_db["transaction_id"]})
        sql.sql_update_one("sales", {"been_refunded": True}, {"sales_item_id": self.sale_db["sales_item_id"]})
        if not self.roll_back_domain():
            return False, "Roll back domain failed"

        return True, refund_row_id

    def roll_back_domain(self):
        return True

    def log_event(self):
        mysql.event_log({
            "event_type":
            self.refund_db['sales_type'],
            "notes": (f"Refund: {self.dom_db['name']} refund {self.refund_db['sales_type']}" +
                      f"for {self.refund_db['num_years']} yrs"),
            "domain_id":
            self.dom_db["domain_id"],
            "user_id":
            self.dom_db["user_id"],
            "who_did_it":
            "admin",
            "from_where":
            "localhost"
        })


def main():
    sql.connect("admin")
    refund = Refund()
    print(refund.run_refund(int(sys.argv[1])))


if __name__ == "__main__":
    main()
