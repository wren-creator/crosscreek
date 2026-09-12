#!/usr/bin/env python3
"""hmi-water: Cross Creek RO demineralisation plant HMI.

Thin operator front-end over plc-water's Modbus interface, styled after a
STEMENS SIMATIX panel "Plant Overview". Deliberate weaknesses, driven by env:
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
PLC_PORT = int(os.environ.get("PLC_MODBUS_PORT", "10502"))
DEFAULT_CREDS = os.environ.get("DEFAULT_CREDS", "1") == "1"
VERBOSE = os.environ.get("VERBOSE_HMI_ERRORS", "1") == "1"
ADMIN_USER = os.environ.get("HMI_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("HMI_ADMIN_PASS", "admin")

app = Flask(__name__)
app.secret_key = os.environ.get("HMI_SECRET", "crosscreek-water-hmi")
_client = ModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=2)

# setpoint name -> (holding register, scale). value * scale is written.
SP = {
    "loop_press": (W.HR_LOOP_PRESS_SP_BAR_X100, 100),
    "tank_lo": (W.HR_TANK_LO_SP_PCT, 1),
    "tank_hi": (W.HR_TANK_HI_SP_PCT, 1),
    "antiscalant_rate": (W.HR_ANTISCALANT_RATE_LH_X10, 10),
    "naoh_rate": (W.HR_NAOH_RATE_LH_X10, 10),
    "cond_limit": (W.HR_COND_LIMIT_US_X100, 100),
    "ro_recovery": (W.HR_RO_RECOVERY_SP_PCT, 1),
}


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
        body = ("HMI fault\n\n" + "".join(traceback.format_exception(exc))
                + "\n\nplc-water tag map:\n" + (W.__doc__ or ""))
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
        u, p = request.form.get("username", ""), request.form.get("password", "")
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
    co = c.read_coils(0, 24, slave=1)
    di = c.read_discrete_inputs(0, 16, slave=1)
    ir = c.read_input_registers(0, 16, slave=1)
    if any(r.isError() for r in (co, di, ir)):
        return jsonify(error="plc unreachable"), 502
    b, d = co.bits, di.bits
    g = lambda a: ir.registers[a] / 100.0
    return jsonify(
        cpu_run=bool(b[W.CO_CPU_RUN]),
        equipment=dict(
            P101=bool(b[W.CO_P101_ANTISCALANT]), P102=bool(b[W.CO_P102_FEED]),
            P301=bool(b[W.CO_P301_RO1_HP]), P302=bool(b[W.CO_P302_RO2]),
            P401=bool(b[W.CO_P401_LOOP]), UV=bool(b[W.CO_UV401]),
        ),
        mode={k: ("HAND" if b[v] else "AUTO") for k, v in W.HAND_COIL.items()},
        seq={k: bool(b[v]) for k, v in W.SEQ_COIL.items()},
        release=dict(
            abnahme=bool(b[W.CO_ABNAHME]), ok=bool(b[W.CO_RELEASE]),
            bypass=bool(b[W.CO_BYPASS_RELEASE_ILK]),
        ),
        alarms=dict(
            tank_low=bool(d[W.DI_TANK_LOW]), tank_high=bool(d[W.DI_TANK_HIGH]),
            loop_press_low=bool(d[W.DI_LOOP_PRESS_LOW]),
            cond_high_ro2=bool(d[W.DI_COND_HIGH_RO2]),
            cond_high_loop=bool(d[W.DI_COND_HIGH_LOOP]),
            uv_fault=bool(d[W.DI_UV_FAULT]),
            feed_flow_low=bool(d[W.DI_FEED_FLOW_LOW]),
            antiscalant_low=bool(d[W.DI_ANTISCALANT_LOW]),
            naoh_low=bool(d[W.DI_NAOH_LOW]),
            release_blocked=bool(d[W.DI_RELEASE_BLOCKED]),
            comms_fault=bool(d[W.DI_COMMS_FAULT]),
        ),
        pv=dict(
            feed_flow_m3h=round(g(W.IR_FEED_FLOW_M3H_X100), 2),
            feed_press_bar=round(g(W.IR_FEED_PRESS_BAR_X100), 2),
            ro1_cond_us=round(g(W.IR_RO1_COND_US_X100), 1),
            ro2_cond_us=round(g(W.IR_RO2_COND_US_X100), 2),
            ro2_press_bar=round(g(W.IR_RO2_PRESS_BAR_X100), 1),
            ro_recovery_pct=round(g(W.IR_RO_RECOVERY_PCT_X100), 0),
            di_tank_pct=round(g(W.IR_DI_TANK_PCT_X100), 1),
            loop_press_bar=round(g(W.IR_LOOP_PRESS_BAR_X100), 2),
            loop_flow_m3h=round(g(W.IR_LOOP_FLOW_M3H_X100), 2),
            loop_ret_cond_us=round(g(W.IR_LOOP_RET_COND_US_X100), 2),
            antiscalant_tank_pct=round(g(W.IR_ANTISCALANT_TANK_PCT_X100), 0),
            naoh_tank_pct=round(g(W.IR_NAOH_TANK_PCT_X100), 0),
            uv_intensity_pct=round(g(W.IR_UV_INTENSITY_PCT_X100), 0),
        ),
        sp=dict(
            loop_press=round(g(W.IR_LOOP_PRESS_SP_BAR_X100), 2),
            cond_limit=round(g(W.IR_COND_LIMIT_US_X100), 2),
        ),
        cond_limit_design=W.COND_LIMIT_DEFAULT_US,
    )


@app.post("/api/cmd")
def api_cmd():
    if not session.get("user"):
        return jsonify(error="auth required"), 401
    c = plc()
    cmd = request.json or {}
    action = cmd.get("action")
    if action == "mode":
        c.write_coil(W.HAND_COIL[cmd["which"]], cmd["hand"] == "HAND", slave=1)
    elif action == "pump":
        c.write_coil(W.RUN_COIL[cmd["which"]], bool(cmd["on"]), slave=1)
    elif action == "seq":
        c.write_coil(W.SEQ_COIL[cmd["which"]], bool(cmd["on"]), slave=1)
    elif action == "abnahme":
        c.write_coil(W.CO_ABNAHME, bool(cmd["on"]), slave=1)
    elif action == "sp":
        reg, scale = SP[cmd["name"]]
        c.write_register(reg, int(round(float(cmd["value"]) * scale)), slave=1)
    else:
        return jsonify(error="unknown action"), 400
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)
