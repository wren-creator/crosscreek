#!/usr/bin/env python3
"""plc-water: Cross Creek RO demineralisation plant soft PLC.

Three concurrent parts:
  * a real Modbus/TCP server on :502 (the field protocol students attack)
  * an OpenPLC-style scan loop that runs the control program every 200 ms
  * a runtime web UI on :8080 (view program, stop/start CPU, upload program)

Deliberate weaknesses, driven by env:
  MODBUS_WRITE_OPEN=1  no command validation in the program; the keyswitch is
                       in REMOTE so the web UI will accept a program upload
  DEFAULT_CREDS=1      web UI accepts openplc/openplc
"""
import importlib.util
import os
import threading
import time
from functools import wraps

from flask import Flask, Response, jsonify, request
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartTcpServer

import mapfile as M

WRITE_OPEN = os.environ.get("MODBUS_WRITE_OPEN", "1") == "1"
DEFAULT_CREDS = os.environ.get("DEFAULT_CREDS", "1") == "1"
PLC_PASS = os.environ.get("PLC_WATER_PASS", "1100")
RUNTIME_DIR = "/plc/logic/runtime"
ACTIVE_PATH = os.path.join(RUNTIME_DIR, "active.py")
GOLDEN_PATH = "/plc/logic/golden_water.py"

# --- Modbus datastore ------------------------------------------------------
_slave = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 32),
    co=ModbusSequentialDataBlock(0, [0] * 40),
    hr=ModbusSequentialDataBlock(0, [0] * 64),
    ir=ModbusSequentialDataBlock(0, [0] * 32),
    zero_mode=True,
)
CTX = ModbusServerContext(slaves={1: _slave}, single=False)
_lock = threading.Lock()


def rd(fc, addr, count=1):
    with _lock:
        return CTX[1].getValues(fc, addr, count=count)


def wr(fc, addr, values):
    with _lock:
        CTX[1].setValues(fc, addr, values)


def _seed():
    wr(3, M.HR_LOOP_PRESS_SP_BAR_X100, [int(M.DEFAULT_LOOP_PRESS_BAR * 100)])
    wr(3, M.HR_TANK_LO_SP_PCT, [M.DEFAULT_TANK_LO_PCT])
    wr(3, M.HR_TANK_HI_SP_PCT, [M.DEFAULT_TANK_HI_PCT])
    wr(3, M.HR_ANTISCALANT_RATE_LH_X10, [int(M.DEFAULT_ANTISCALANT_LH * 10)])
    wr(3, M.HR_NAOH_RATE_LH_X10, [int(M.DEFAULT_NAOH_LH * 10)])
    wr(3, M.HR_COND_LIMIT_US_X100, [int(M.COND_LIMIT_DEFAULT_US * 100)])
    wr(3, M.HR_RO_RECOVERY_SP_PCT, [M.DEFAULT_RO_RECOVERY_PCT])
    # plausible field values so the plant looks alive before process-sim connects
    wr(3, M.HR_DI_TANK_PCT_X100, [7000])
    wr(3, M.HR_RO1_COND_US_X100, [1500])
    wr(3, M.HR_RO2_COND_US_X100, [120])
    wr(3, M.HR_LOOP_PRESS_BAR_X100, [int(M.DEFAULT_LOOP_PRESS_BAR * 100)])
    wr(3, M.HR_LOOP_RET_COND_US_X100, [90])
    wr(3, M.HR_UV_INTENSITY_PCT_X100, [9500])
    wr(3, M.HR_ANTISCALANT_TANK_PCT_X100, [8000])
    wr(3, M.HR_NAOH_TANK_PCT_X100, [8000])
    wr(1, M.CO_CPU_RUN, [1])
    wr(1, M.CO_SEQ_LOOP, [1])
    wr(1, M.CO_ABNAHME, [1])


class IO:
    """Live view handed to control(). Reads pull from the datastore; the
    actuator/sequence coils are pushed back after control() returns."""

    def __init__(self):
        hr = rd(3, 0, 24)
        co = rd(1, 0, 24)
        g = lambda a: hr[a] / 100.0
        self.tank_lo_sp = hr[M.HR_TANK_LO_SP_PCT]
        self.tank_hi_sp = hr[M.HR_TANK_HI_SP_PCT]
        self.loop_press_sp = g(M.HR_LOOP_PRESS_SP_BAR_X100)
        self.cond_limit_us = g(M.HR_COND_LIMIT_US_X100)
        self.antiscalant_rate_lh = hr[M.HR_ANTISCALANT_RATE_LH_X10] / 10.0
        self.naoh_rate_lh = hr[M.HR_NAOH_RATE_LH_X10] / 10.0
        self.feed_flow_m3h = g(M.HR_FEED_FLOW_M3H_X100)
        self.feed_press_bar = g(M.HR_FEED_PRESS_BAR_X100)
        self.ro1_cond_us = g(M.HR_RO1_COND_US_X100)
        self.ro2_cond_us = g(M.HR_RO2_COND_US_X100)
        self.ro2_press_bar = g(M.HR_RO2_PRESS_BAR_X100)
        self.ro_recovery_pct = g(M.HR_RO_RECOVERY_PCT_X100)
        self.di_tank_pct = g(M.HR_DI_TANK_PCT_X100)
        self.loop_press_bar = g(M.HR_LOOP_PRESS_BAR_X100)
        self.loop_flow_m3h = g(M.HR_LOOP_FLOW_M3H_X100)
        self.loop_ret_cond_us = g(M.HR_LOOP_RET_COND_US_X100)
        self.antiscalant_tank_pct = g(M.HR_ANTISCALANT_TANK_PCT_X100)
        self.naoh_tank_pct = g(M.HR_NAOH_TANK_PCT_X100)
        self.uv_intensity_pct = g(M.HR_UV_INTENSITY_PCT_X100)
        # constants the program reads
        self.cond_hard_limit = M.COND_ALARM_HARD_US
        self.uv_min_intensity = M.UV_MIN_INTENSITY_PCT
        # current outputs (so HAND holds them across scans)
        self.p101_antiscalant = bool(co[M.CO_P101_ANTISCALANT])
        self.p102_feed = bool(co[M.CO_P102_FEED])
        self.p301_ro1 = bool(co[M.CO_P301_RO1_HP])
        self.p302_ro2 = bool(co[M.CO_P302_RO2])
        self.p401_loop = bool(co[M.CO_P401_LOOP])
        self.uv401 = bool(co[M.CO_UV401])
        self.freigabe = bool(co[M.CO_FREIGABE])
        self.seq_ro = bool(co[M.CO_SEQ_RO])
        self.seq_loop = bool(co[M.CO_SEQ_LOOP])
        self.seq_cip = bool(co[M.CO_SEQ_CIP])
        self.seq_sanitise = bool(co[M.CO_SEQ_SANITISE])
        self.bypass_release_ilk = bool(co[M.CO_BYPASS_RELEASE_ILK])
        # HAND flags
        self.p101_hand = bool(co[M.CO_P101_HAND])
        self.p102_hand = bool(co[M.CO_P102_HAND])
        self.p301_hand = bool(co[M.CO_P301_HAND])
        self.p302_hand = bool(co[M.CO_P302_HAND])
        self.p401_hand = bool(co[M.CO_P401_HAND])
        self.uv_hand = bool(co[M.CO_UV_HAND])
        self.ro_valves_hand = bool(co[M.CO_RO_VALVES_HAND])
        self.loop_valves_hand = bool(co[M.CO_LOOP_VALVES_HAND])

    def commit(self):
        wr(1, M.CO_P101_ANTISCALANT, [int(self.p101_antiscalant)])
        wr(1, M.CO_P102_FEED, [int(self.p102_feed)])
        wr(1, M.CO_P301_RO1_HP, [int(self.p301_ro1)])
        wr(1, M.CO_P302_RO2, [int(self.p302_ro2)])
        wr(1, M.CO_P401_LOOP, [int(self.p401_loop)])
        wr(1, M.CO_UV401, [int(self.uv401)])
        wr(1, M.CO_FREIGABE, [int(self.freigabe)])
        wr(1, M.CO_SEQ_RO, [int(self.seq_ro)])
        wr(1, M.CO_SEQ_LOOP, [int(self.seq_loop)])


def load_active():
    spec = importlib.util.spec_from_file_location("active", ACTIVE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_active = {"mod": None, "name": "(none)", "loaded_at": 0.0}


def reload_active():
    mod = load_active()
    _active["mod"] = mod
    _active["name"] = getattr(mod, "PROGRAM_NAME", "unnamed")
    _active["loaded_at"] = time.time()
    print(f"[plc-water] loaded program: {_active['name']}")


def _harden():
    """Command validation, only active when MODBUS_WRITE_OPEN=0. The release
    conductivity limit and the loop pressure setpoint are range-checked in the
    program, and the interlock-bypass coil is not remotely settable."""
    lim = rd(3, M.HR_COND_LIMIT_US_X100)[0]
    wr(3, M.HR_COND_LIMIT_US_X100, [max(50, min(lim, 500))])       # 0.50-5.00 uS/cm
    sp = rd(3, M.HR_LOOP_PRESS_SP_BAR_X100)[0]
    wr(3, M.HR_LOOP_PRESS_SP_BAR_X100, [max(200, min(sp, 500))])   # 2.0-5.0 bar
    na = rd(3, M.HR_NAOH_RATE_LH_X10)[0]
    wr(3, M.HR_NAOH_RATE_LH_X10, [max(0, min(na, 80))])
    an = rd(3, M.HR_ANTISCALANT_RATE_LH_X10)[0]
    wr(3, M.HR_ANTISCALANT_RATE_LH_X10, [max(0, min(an, 60))])
    wr(1, M.CO_BYPASS_RELEASE_ILK, [0])


def scan_loop():
    scan = 0
    while True:
        t0 = time.time()
        try:
            if rd(1, M.CO_CPU_RUN)[0]:
                if not WRITE_OPEN:
                    _harden()
                io = IO()
                _active["mod"].control(io)
                io.commit()

                # derived discrete inputs
                wr(2, M.DI_TANK_LOW, [int(io.di_tank_pct <= io.tank_lo_sp)])
                wr(2, M.DI_TANK_HIGH, [int(io.di_tank_pct >= io.tank_hi_sp)])
                wr(2, M.DI_LOOP_PRESS_LOW,
                   [int(io.loop_press_bar < io.loop_press_sp - 0.5)])
                wr(2, M.DI_COND_HIGH_RO2, [int(io.ro2_cond_us > io.cond_limit_us)])
                wr(2, M.DI_COND_HIGH_LOOP,
                   [int(io.loop_ret_cond_us > io.cond_limit_us)])
                wr(2, M.DI_UV_FAULT,
                   [int(io.uv_intensity_pct < io.uv_min_intensity)])
                wr(2, M.DI_FEED_FLOW_LOW,
                   [int(io.p102_feed and io.feed_flow_m3h < 0.5)])
                wr(2, M.DI_ANTISCALANT_LOW, [int(io.antiscalant_tank_pct < 10.0)])
                wr(2, M.DI_NAOH_LOW, [int(io.naoh_tank_pct < 10.0)])
                wr(2, M.DI_RELEASE_BLOCKED, [int(not io.freigabe)])

            # operator-facing mirror (updates even in STOP)
            hr = rd(3, 0, 24)
            hb = hr[M.HR_SIM_HEARTBEAT]
            now = time.time()
            if hb != scan_loop.last_hb:
                scan_loop.last_hb = hb
                scan_loop.last_hb_change = now
            wr(2, M.DI_COMMS_FAULT, [int(now - scan_loop.last_hb_change > 5.0)])
            mirror = [
                (M.IR_FEED_FLOW_M3H_X100, M.HR_FEED_FLOW_M3H_X100),
                (M.IR_FEED_PRESS_BAR_X100, M.HR_FEED_PRESS_BAR_X100),
                (M.IR_RO1_COND_US_X100, M.HR_RO1_COND_US_X100),
                (M.IR_RO2_COND_US_X100, M.HR_RO2_COND_US_X100),
                (M.IR_RO2_PRESS_BAR_X100, M.HR_RO2_PRESS_BAR_X100),
                (M.IR_RO_RECOVERY_PCT_X100, M.HR_RO_RECOVERY_PCT_X100),
                (M.IR_DI_TANK_PCT_X100, M.HR_DI_TANK_PCT_X100),
                (M.IR_LOOP_PRESS_BAR_X100, M.HR_LOOP_PRESS_BAR_X100),
                (M.IR_LOOP_FLOW_M3H_X100, M.HR_LOOP_FLOW_M3H_X100),
                (M.IR_LOOP_RET_COND_US_X100, M.HR_LOOP_RET_COND_US_X100),
                (M.IR_ANTISCALANT_TANK_PCT_X100, M.HR_ANTISCALANT_TANK_PCT_X100),
                (M.IR_NAOH_TANK_PCT_X100, M.HR_NAOH_TANK_PCT_X100),
                (M.IR_UV_INTENSITY_PCT_X100, M.HR_UV_INTENSITY_PCT_X100),
                (M.IR_LOOP_PRESS_SP_BAR_X100, M.HR_LOOP_PRESS_SP_BAR_X100),
                (M.IR_COND_LIMIT_US_X100, M.HR_COND_LIMIT_US_X100),
            ]
            for ir_a, hr_a in mirror:
                wr(4, ir_a, [hr[hr_a]])
            scan += 1
            wr(4, M.IR_CPU_SCAN_COUNT, [scan & 0xFFFF])
        except Exception as exc:  # keep the CPU alive through a bad program
            print(f"[plc-water] scan fault: {exc}")
        time.sleep(max(0.0, 0.2 - (time.time() - t0)))


scan_loop.last_hb = -1
scan_loop.last_hb_change = time.time()

# --- runtime web UI ------------------------------------------------------
app = Flask(__name__)


def _check_auth(u, p):
    if DEFAULT_CREDS:
        return u == "openplc" and p == "openplc"
    return u == "openplc" and p == PLC_PASS


def auth_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return Response(
                "Authentication required", 401,
                {"WWW-Authenticate": 'Basic realm="OpenPLC Runtime"'},
            )
        return f(*a, **kw)
    return wrapper


PAGE = """<!doctype html><meta charset=utf-8><title>OpenPLC Runtime - plc-water</title>
<style>body{{font-family:monospace;background:#10151a;color:#cde;margin:2em;max-width:820px}}
h1{{color:#5db}}pre{{background:#0a0f13;padding:1em;overflow:auto;border:1px solid #244}}
.k{{color:#fb6}}form{{margin:1em 0}}a{{color:#5db}}</style>
<h1>OpenPLC Runtime &mdash; Cross Creek RO plant</h1>
<p>CPU: <b>{cpu}</b> &nbsp; Keyswitch: <b class=k>{keysw}</b> &nbsp;
Program: <b>{prog}</b> &nbsp; Scan: {scan}</p>
<form method=post action=/cpu><button name=state value=stop>Stop CPU</button>
<button name=state value=start>Start CPU</button></form>
<h3>Upload program</h3>
<form method=post action=/upload-program enctype=multipart/form-data>
<input type=file name=program><button>Upload &amp; run</button></form>
<p>{msg}</p>
<h3>Running program</h3><pre>{listing}</pre>
"""


@app.get("/")
@auth_required
def home():
    cpu = "RUN" if rd(1, M.CO_CPU_RUN)[0] else "STOP"
    keysw = "REMOTE" if WRITE_OPEN else "RUN (locked)"
    try:
        listing = open(ACTIVE_PATH).read()
    except OSError:
        listing = "(no program)"
    return PAGE.format(
        cpu=cpu, keysw=keysw, prog=_active["name"],
        scan=rd(4, M.IR_CPU_SCAN_COUNT)[0], msg="", listing=listing,
    )


@app.get("/health")
def health():
    return "ok", 200


@app.get("/api/state")
def api_state():
    co = rd(1, 0, 24)
    di = rd(2, 0, 16)
    ir = rd(4, 0, 16)
    g = lambda a: ir[a] / 100.0
    return jsonify(
        cpu_run=bool(co[M.CO_CPU_RUN]),
        program=_active["name"],
        keyswitch="REMOTE" if WRITE_OPEN else "RUN",
        equipment=dict(
            P101=bool(co[M.CO_P101_ANTISCALANT]),
            P102=bool(co[M.CO_P102_FEED]),
            P301=bool(co[M.CO_P301_RO1_HP]),
            P302=bool(co[M.CO_P302_RO2]),
            P401=bool(co[M.CO_P401_LOOP]),
            UV=bool(co[M.CO_UV401]),
        ),
        mode=dict(
            P101="HAND" if co[M.CO_P101_HAND] else "AUTO",
            P102="HAND" if co[M.CO_P102_HAND] else "AUTO",
            P301="HAND" if co[M.CO_P301_HAND] else "AUTO",
            P302="HAND" if co[M.CO_P302_HAND] else "AUTO",
            P401="HAND" if co[M.CO_P401_HAND] else "AUTO",
            UV="HAND" if co[M.CO_UV_HAND] else "AUTO",
            RO_VALVES="HAND" if co[M.CO_RO_VALVES_HAND] else "AUTO",
            LOOP_VALVES="HAND" if co[M.CO_LOOP_VALVES_HAND] else "AUTO",
        ),
        seq=dict(
            RO=bool(co[M.CO_SEQ_RO]),
            LOOP=bool(co[M.CO_SEQ_LOOP]),
            CIP=bool(co[M.CO_SEQ_CIP]),
            SANITISE=bool(co[M.CO_SEQ_SANITISE]),
        ),
        release=dict(
            abnahme=bool(co[M.CO_ABNAHME]),
            freigabe=bool(co[M.CO_FREIGABE]),
            bypass_interlock=bool(co[M.CO_BYPASS_RELEASE_ILK]),
        ),
        alarms=dict(
            tank_low=bool(di[M.DI_TANK_LOW]),
            tank_high=bool(di[M.DI_TANK_HIGH]),
            loop_press_low=bool(di[M.DI_LOOP_PRESS_LOW]),
            cond_high_ro2=bool(di[M.DI_COND_HIGH_RO2]),
            cond_high_loop=bool(di[M.DI_COND_HIGH_LOOP]),
            uv_fault=bool(di[M.DI_UV_FAULT]),
            feed_flow_low=bool(di[M.DI_FEED_FLOW_LOW]),
            antiscalant_low=bool(di[M.DI_ANTISCALANT_LOW]),
            naoh_low=bool(di[M.DI_NAOH_LOW]),
            release_blocked=bool(di[M.DI_RELEASE_BLOCKED]),
            comms_fault=bool(di[M.DI_COMMS_FAULT]),
        ),
        pv=dict(
            feed_flow_m3h=round(g(M.IR_FEED_FLOW_M3H_X100), 2),
            feed_press_bar=round(g(M.IR_FEED_PRESS_BAR_X100), 2),
            ro1_cond_us=round(g(M.IR_RO1_COND_US_X100), 2),
            ro2_cond_us=round(g(M.IR_RO2_COND_US_X100), 3),
            ro2_press_bar=round(g(M.IR_RO2_PRESS_BAR_X100), 2),
            ro_recovery_pct=round(g(M.IR_RO_RECOVERY_PCT_X100), 1),
            di_tank_pct=round(g(M.IR_DI_TANK_PCT_X100), 1),
            loop_press_bar=round(g(M.IR_LOOP_PRESS_BAR_X100), 2),
            loop_flow_m3h=round(g(M.IR_LOOP_FLOW_M3H_X100), 2),
            loop_ret_cond_us=round(g(M.IR_LOOP_RET_COND_US_X100), 3),
            antiscalant_tank_pct=round(g(M.IR_ANTISCALANT_TANK_PCT_X100), 1),
            naoh_tank_pct=round(g(M.IR_NAOH_TANK_PCT_X100), 1),
            uv_intensity_pct=round(g(M.IR_UV_INTENSITY_PCT_X100), 1),
        ),
        sp=dict(
            loop_press=round(g(M.IR_LOOP_PRESS_SP_BAR_X100), 2),
            cond_limit=round(g(M.IR_COND_LIMIT_US_X100), 2),
        ),
        limits=dict(cond_limit_us=M.COND_LIMIT_DEFAULT_US,
                    uv_min=M.UV_MIN_INTENSITY_PCT),
    )


@app.post("/cpu")
@auth_required
def cpu():
    wr(1, M.CO_CPU_RUN, [1 if request.form.get("state") == "start" else 0])
    return home()


@app.post("/upload-program")
@auth_required
def upload_program():
    if not WRITE_OPEN:
        return Response(
            "Keyswitch is in RUN. Program downloads are disabled.\n", 403
        )
    f = request.files.get("program")
    if not f:
        return Response("no file\n", 400)
    data = f.read().decode("utf-8", "replace")
    if "def control(" not in data:
        return Response(
            "This runtime executes a control(io) module. Compile your ST first.\n",
            400,
        )
    with open(ACTIVE_PATH, "w") as out:
        out.write(data)
    reload_active()
    return Response(f"program accepted and running: {_active['name']}\n", 200)


def main():
    _seed()
    reload_active()
    threading.Thread(target=scan_loop, daemon=True).start()
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=8080, threaded=True,
                               use_reloader=False),
        daemon=True,
    ).start()
    print("[plc-water] Modbus/TCP on :502, runtime UI on :8080")
    StartTcpServer(context=CTX, address=("0.0.0.0", 502))


if __name__ == "__main__":
    main()
