#!/usr/bin/env python3
"""hmi-water: Cross Creek water plant HMI.

Thin operator front-end over plc-water's Modbus interface. Deliberate
weaknesses, driven by env:
  DEFAULT_CREDS=1       admin / admin
  VERBOSE_HMI_ERRORS=1  exceptions render the full traceback and the tag map
"""
import os
import traceback

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for,
)
from pymodbus.client import ModbusTcpClient

import watermap as W

PLC_HOST = os.environ.get("PLC_MODBUS_HOST", "172.30.41.10")
PLC_PORT = int(os.environ.get("PLC_MODBUS_PORT", "502"))
DEFAULT_CREDS = os.environ.get("DEFAULT_CREDS", "1") == "1"
VERBOSE = os.environ.get("VERBOSE_HMI_ERRORS", "1") == "1"
ADMIN_USER = os.environ.get("HMI_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("HMI_ADMIN_PASS", "admin")

app = Flask(__name__)
app.secret_key = os.environ.get("HMI_SECRET", "crosscreek-water-hmi")

_client = ModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=2)


def plc():
    if not _client.connected:
        _client.connect()
    return _client


def _creds_ok(u, p):
    if DEFAULT_CREDS and u == "admin" and p == "admin":
        return True
    return u == ADMIN_USER and p == ADMIN_PASS


@app.errorhandler(Exception)
def on_error(exc):
    if VERBOSE:
        body = (
            "HMI fault\n\n"
            + "".join(traceback.format_exception(exc))
            + "\n\nplc-water tag map:\n"
            + (W.__doc__ or "")
        )
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
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if _creds_ok(u, p):
            session["user"] = u
            return redirect(url_for("index"))
        err = "invalid credentials"
    return render_template("login.html", err=err, hint=DEFAULT_CREDS)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/api/state")
def api_state():
    c = plc()
    co = c.read_coils(0, 8, slave=1)
    di = c.read_discrete_inputs(0, 8, slave=1)
    ir = c.read_input_registers(0, 8, slave=1)
    hr = c.read_holding_registers(0, 20, slave=1)
    if any(r.isError() for r in (co, di, ir, hr)):
        return jsonify(error="plc unreachable"), 502
    return jsonify(
        cpu_run=bool(co.bits[W.CO_CPU_RUN]),
        pumps=dict(
            intake=bool(co.bits[W.CO_INTAKE_PUMP]),
            distribution=bool(co.bits[W.CO_DIST_PUMP]),
            dosing=bool(co.bits[W.CO_DOSE_ENABLE]),
        ),
        mode=dict(
            intake="HAND" if co.bits[W.CO_INTAKE_HAND] else "AUTO",
            distribution="HAND" if co.bits[W.CO_DIST_HAND] else "AUTO",
            dosing="HAND" if co.bits[W.CO_DOSE_HAND] else "AUTO",
        ),
        alarms=dict(
            level_low=bool(di.bits[W.DI_LEVEL_LOW]),
            level_high=bool(di.bits[W.DI_LEVEL_HIGH]),
            press_low=bool(di.bits[W.DI_PRESS_LOW]),
            overdose=bool(di.bits[W.DI_OVERDOSE]),
            comms_fault=bool(di.bits[W.DI_COMMS_FAULT]),
        ),
        pv=dict(
            raw_level_pct=round(ir.registers[W.IR_RAW_TANK_LEVEL_PCT_X100] / 100.0, 1),
            treated_level_pct=round(ir.registers[W.IR_TREATED_TANK_LEVEL_PCT_X100] / 100.0, 1),
            chlorine_ppm=round(ir.registers[W.IR_CHLORINE_PPM_X100] / 100.0, 2),
            header_psi=round(ir.registers[W.IR_DIST_PRESS_PSI_X100] / 100.0, 1),
            flow_gpm=round(ir.registers[W.IR_FLOW_GPM_X10] / 10.0, 0),
        ),
        sp=dict(
            dose_ppm=round(hr.registers[W.HR_DOSE_SETPOINT_PPM_X100] / 100.0, 2),
            press_target=hr.registers[W.HR_DIST_PRESS_TARGET_PSI],
        ),
        safe_max_ppm=W.SAFE_MAX_PPM,
    )


@app.post("/api/cmd")
def api_cmd():
    if not session.get("user"):
        return jsonify(error="auth required"), 401
    c = plc()
    cmd = request.json or {}
    action = cmd.get("action")
    pump_coil = {"intake": W.CO_INTAKE_PUMP, "distribution": W.CO_DIST_PUMP,
                 "dosing": W.CO_DOSE_ENABLE}
    hand_coil = {"intake": W.CO_INTAKE_HAND, "distribution": W.CO_DIST_HAND,
                 "dosing": W.CO_DOSE_HAND}
    if action == "mode":
        # AUTO / HAND per device. Taking a pump to HAND is what lets the
        # start/stop buttons stick; in AUTO the control program owns the output.
        c.write_coil(hand_coil[cmd["which"]], cmd["hand"] == "HAND", slave=1)
    elif action == "pump":
        c.write_coil(pump_coil[cmd["which"]], bool(cmd["on"]), slave=1)
    elif action == "dose_setpoint":
        c.write_register(
            W.HR_DOSE_SETPOINT_PPM_X100, int(float(cmd["ppm"]) * 100), slave=1
        )
    elif action == "press_target":
        c.write_register(W.HR_DIST_PRESS_TARGET_PSI, int(cmd["psi"]), slave=1)
    else:
        return jsonify(error="unknown action"), 400
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)
