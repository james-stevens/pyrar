#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible,
# contact me for more information

import json
import xmltodict
import os
import sys
import errno
import socket
import ssl
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from inspect import currentframe as czz, getframeinfo as gzz

import flask
import lib.policy as policy
from lib.log import log, init as log_init
from lib.policy import this_policy as policy


CLIENT_PEM_DIR = os.environ["BASE"] + "/pems"
LOGINS_FILE = os.environ["BASE"] + "/etc/logins.json"


application = flask.Flask("EPP/REST/API")
conn = None
idSeq = 0

EPP_PORT = 700

EPP_PKT_LEN_BYTES = 4
NETWORK_BYTE_ORDER = "big"

if "PYRAR_REGISTRY" not in os.environ:
    raise ValueError("No `PYRAR_REGISTRY` specified")

if not os.path.isfile(LOGINS_FILE):
    raise ValueError(f"Logins file `{LOGINS_FILE}` is missing")

with open(LOGINS_FILE, "r") as fd:
    logins = json.load(fd)

this_reg = os.environ["PYRAR_REGISTRY"]
if this_reg not in logins:
    raise ValueError(f"Registry '{this_reg}' not in '{LOGINS_FILE}'")

this_login = logins[this_reg]
for item in ["username", "password", "server"]:
    if item not in this_login:
        raise ValueError(f"Item '{item}' missing from registry '{this_reg}'")

client_pem = f"{CLIENT_PEM_DIR}/{this_reg}.pem"
if not os.path.isfile(client_pem):
    raise ValueError(f"Client PEM file for '{this_reg}' at '{client_pem}' not found")

log_init(policy.policy("facility_epp_api"), False, policy.policy("log_epp_api"))

jobInterval = 120

def keepAlive():
    jsonRequest({"hello": None}, "keepAlive")


scheduler = None
if jobInterval > 0:
    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.start(paused=True)
    job = scheduler.add_job(keepAlive, 'interval', minutes=jobInterval, id='keepAlive')


def closeEPP():
    global conn
    if conn is None:
        return
    ret, js = xmlRequest({"logout": None})
    flask.Response(js)
    log(f"Logout {ret}", gzz(czz()))
    conn.close()


def gracefulExit():
    closeEPP()
    sys.exit(errno.EINTR)


atexit.register(gracefulExit)


class Empty:
    pass


def abort(err_no, message):
    response = flask.jsonify({"error": {"message": message}})
    response.status_code = err_no
    return response


def hexId(i):
    return hex(int(i))[2:].upper()


def makeXML(cmd):
    global idSeq
    idSeq = idSeq + 1
    clTRID = "ID:" + hexId(time.time()) + "_" + hexId(os.getpid()) + "_" + hexId(idSeq)

    verb = "command"
    if "hello" in cmd:
        verb = "hello"
        cmd = None
    else:
        cmd["clTRID"] = clTRID

    xml = xmltodict.unparse({"epp": {"@xmlns": "urn:ietf:params:xml:ns:epp-1.0", verb: cmd}})
    return clTRID, ((EPP_PKT_LEN_BYTES + len(xml)).to_bytes(EPP_PKT_LEN_BYTES, NETWORK_BYTE_ORDER) +
                    bytearray(xml, 'utf-8'))


def makeLogin(username, password):
    return {
        "login": {
            "clID": username,
            "pw": password,
            "options": {
                "version": "1.0",
                "lang": "en"
            },
            "svcs": {
                "objURI": [
                    "urn:ietf:params:xml:ns:domain-1.0", "urn:ietf:params:xml:ns:contact-1.0",
                    "urn:ietf:params:xml:ns:host-1.0"
                ],
                "svcExtension": {
                    "extURI": ["urn:ietf:params:xml:ns:secDNS-1.1", "urn:ietf:params:xml:ns:fee-1.0"]
                }
            }
        }
    }


def jsonReply(conn, clTRID):
    buf = conn.recv(EPP_PKT_LEN_BYTES)
    if len(buf) == 0:
        return None, None
    lgth = int.from_bytes(buf, NETWORK_BYTE_ORDER)
    buf = conn.recv(lgth)
    if len(buf) == 0:
        return None, None
    js = xmltodict.parse(buf)
    ret = 9999
    if "epp" in js:
        js = js["epp"]

    if "@xmlns" in js:
        del js["@xmlns"]

    if "greeting" in js:
        return 1000, js

    if "response" in js:
        js = js["response"]

    if "result" in js and "@code" in js["result"]:
        ret = int(js["result"]["@code"])

    if "trID" in js and "clTRID" in js["trID"]:
        if js["trID"]["clTRID"] == clTRID:
            del js["trID"]
        else:
            ret = 9990

    return ret, js


def xmlRequest(js):
    global conn
    clTRID, xml = makeXML(js)
    try:
        conn.sendall(xml)
        return jsonReply(conn, clTRID)
    except Exception as e:
        return None, None


@application.route('/api/epp/v1.0/close', methods=['GET'])
@application.route('/epp/api/v1.0/close', methods=['GET'])
def handleCloseRequest():
    closeEPP()
    return abort(200, "Session Closed")


@application.route('/api/epp/v1.0/finish', methods=['GET'])
@application.route('/epp/api/v1.0/finish', methods=['GET'])
def handleFinsihRequest():
    gracefulExit()
    return abort(200, "Server Terminated")


def firstDict(thisDict):
    for d in thisDict:
        return d.lower()


def jsonRequest(in_js, addr):
    global conn
    global scheduler

    if conn is None:
        connectToEPP()
        if conn is None:
            return abort(499, f"Failed to connect to EPP Server - `{this_login['server']}`")

    t1 = firstDict(in_js)
    if t1 == "hello":
        t2 = "hello"
    else:
        t2 = firstDict(in_js[t1])
        if t2[0] == "@":
            t2 = in_js[t1][t2]

    if jobInterval > 0 and scheduler is not None:
        scheduler.reschedule_job('keepAlive', trigger='interval', minutes=jobInterval)
        scheduler.resume()

    ret, js = xmlRequest(in_js)

    if ret is None or js is None:
        log(f"Reconnecting to EPP",gzz(czz()))
        conn.close()
        conn = None
        connectToEPP()
        if conn is None:
            return abort(499, "Failed to connect to EPP Server")
        ret, js = xmlRequest(in_js)
        if ret is None or js is None:
            conn.close()
            conn = None
            return abort(499, "Lost connection to EPP Server")

    log(f"User request: {addr} asked '{t1}/{t2}' -> {ret}", gzz(czz()))

    return js


@application.route('/api/epp/v1.0/request', methods=['POST'])
@application.route('/epp/api/v1.0/request', methods=['POST'])
def eppJSON():
    if flask.request.json is None:
        return abort(499, "No JSON data was POSTed")
    return jsonRequest(flask.request.json, flask.request.remote_addr)


def connectToEPP():

    global conn
    global scheduler

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_cert_chain(client_pem)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = context.wrap_socket(s, server_side=False, server_hostname=this_login["server"])

    log(f"Connecting to EPP Server: {this_login['server']}", gzz(czz()))
    try:
        conn.connect((this_login["server"], EPP_PORT))
        conn.setblocking(True)
    except Exception as e:
        log(str(e), gzz(czz()))
        conn.close()
        conn = None
        return

    ret, js = jsonReply(conn, None)
    log(f"Greeting '{this_reg}' gave {ret}", gzz(czz()))

    ret, js = xmlRequest(makeLogin(this_login["username"], this_login["password"]))
    log(f"Login to '{this_reg}' gives {ret}", gzz(czz()))

    if jobInterval > 0 and scheduler is not None:
        scheduler.resume()


if __name__ == "__main__":
    application.run()
