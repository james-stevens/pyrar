#! /usr/bin/python3

import json
import hashlib

ret_js = {
    "payment_id": 4884250695,
    "invoice_id": 4370532081,
    "payment_status": "finished",
    "pay_address": "3KUEfiP63WrGhod5PUzCdMPLe5eArkk5Cy",
    "price_amount": 18.91,
    "price_currency": "usd",
    "pay_amount": 0.00066964,
    "actually_paid": 0,
    "actually_paid_at_fiat": 0,
    "pay_currency": "btc",
    "order_id": "pz0a2E2ShqIGos9K6FJ6EOBTSwfyDU",
    "order_description": "Some Desc",
    "purchase_id": "4688037020",
    "created_at": "2023-03-30T16:32:26.333Z",
    "updated_at": "2023-03-30T16:32:30.483Z",
    "outcome_amount": 0.000594,
    "outcome_currency": "btc"
}
s = json.dumps(ret_js, sort_keys=True, separators=(',', ':'))

print(">>>>" + s + "<<<<")
wanting = ("aed675f86537c33f02059c4a53c1b37be106b0ed1f2220ec0202c12b5893fd1ab50" +
           "ccd0d4c80f31bee9db29acb5fb0030cc98fde7a6a0c21194476cb7d51e794")

hsh = hashlib.sha512()
hsh.update(s.encode("utf-8"))
hsh.update("RYS8ANmpl8eT9aAqjj9xgEhSAycFvLj1".encode("utf-8"))
res = "".join(["{:02x}".format(x) for x in hsh.digest()])

print((res == wanting), res)
