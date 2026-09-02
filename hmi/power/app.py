#!/usr/bin/env python3
"""hmi-power: Cross Creek substation HMI. Thin front-end over plc-power's S7
DB1. DEFAULT_CREDS / VERBOSE_HMI_ERRORS behave as on the water HMI.
"""
import os
import socket
import struct
import traceback

import snap7
from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for,
)

import s7map as S

PLC_HOST = os.environ.get("PLC_S7_HOST", "172.30.41.12")
DEFAULT_CREDS = os.environ.get("DEFAULT_CREDS", "1") == "1"
VERBOSE = os.environ.get("VERBOSE_HMI_ERRORS", "1") == "1"
ADMIN_USER = os.environ.get("HMI_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("HMI_ADMIN_PASS", "admin")

app = Flask(__name__)
app.secret_key = os.environ.get("HMI_SECRET", "crosscreek-power-hmi")
_c = snap7.client.Client()


def plc():
    if not _c.get_connected():
        # snap7's C client needs an IP, not a DNS name
        _c.connect(socket.gethostbyname(PLC_HOST), 0, 1)
    return _c


def _creds_ok(u, p):
    if DEFAULT_CREDS and u == "admin" and p == "admin":
        return True
    return u == ADMIN_USER and p == ADMIN_PASS


@app.errorhandler(Exception)
def on_error(exc):
    if VERBOSE:
        body = "HMI fault\n\n" + "".join(traceback.format_exception(exc))
        body += "\n\nplc-power DB1 map:\n" + (S.__doc__ or "")
        return app.response_class(body, status=500, mimetype="text/plain")
    return app.response_class("internal error", status=500, mimetype="text/plain")


@app.get("/health")
def health():
    return "ok", 200


@app.get("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])


@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if _creds_ok(request.form.get("username", ""), request.form.get("password", "")):
            session["user"] = request.form["username"]
            return redirect(url_for("index"))
        err = "invalid credentials"
    return render_template("login.html", err=err, hint=DEFAULT_CREDS)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/api/state")
def api_state():
    db = plc().db_read(S.DB_NUMBER, 0, S.DB_SIZE)
    st = db[S.BREAKER_STATUS]
    return jsonify(
        cpu_mode="RUN" if db[S.CPU_MODE] == 1 else "STOP",
        breakers=dict(
            feeder=bool(st & (1 << S.BRK_FEEDER)),
            bus_tie=bool(st & (1 << S.BRK_TIE)),
            load=bool(st & (1 << S.BRK_LOAD)),
        ),
        pv=dict(
            freq_hz=round(struct.unpack_from(">h", db, S.BUS_FREQ_X100)[0] / 100.0, 3),
            voltage_kv=round(struct.unpack_from(">h", db, S.BUS_VOLTAGE_KV_X10)[0] / 10.0, 1),
            load_mw=round(struct.unpack_from(">h", db, S.LOAD_MW_X10)[0] / 10.0, 1),
        ),
    )


@app.post("/api/cmd")
def api_cmd():
    if not session.get("user"):
        return jsonify(error="auth required"), 401
    cmd = request.json or {}
    bit = {
        ("feeder", True): S.CMD_FEEDER_CLOSE, ("feeder", False): S.CMD_FEEDER_OPEN,
        ("bus_tie", True): S.CMD_TIE_CLOSE, ("bus_tie", False): S.CMD_TIE_OPEN,
        ("load", True): S.CMD_LOAD_CLOSE, ("load", False): S.CMD_LOAD_OPEN,
    }[(cmd["breaker"], bool(cmd["close"]))]
    plc().db_write(S.DB_NUMBER, S.BREAKER_CMD, bytearray([1 << bit]))
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)
