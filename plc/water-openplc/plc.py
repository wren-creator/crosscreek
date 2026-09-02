#!/usr/bin/env python3
"""plc-water: Cross Creek water plant soft PLC.

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

# --- Modbus datastore --------------------------------------------------------
_slave = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 32),
    co=ModbusSequentialDataBlock(0, [0] * 32),
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
    wr(3, M.HR_DOSE_SETPOINT_PPM_X100, [int(M.DESIGN_PPM * 100)])
    wr(3, M.HR_DIST_PRESS_TARGET_PSI, [M.DEFAULT_PRESS_TARGET_PSI])
    wr(3, M.HR_LEVEL_LOW_SP_PCT, [M.DEFAULT_LOW_SP_PCT])
    wr(3, M.HR_LEVEL_HIGH_SP_PCT, [M.DEFAULT_HIGH_SP_PCT])
    wr(3, M.HR_RAW_TANK_LEVEL_PCT_X100, [6000])
    wr(3, M.HR_TREATED_TANK_LEVEL_PCT_X100, [7000])
    wr(3, M.HR_CHLORINE_PPM_X100, [int(M.DESIGN_PPM * 100)])
    wr(3, M.HR_DIST_PRESS_PSI_X100, [M.DEFAULT_PRESS_TARGET_PSI * 100])
    wr(1, M.CO_CPU_RUN, [1])


# --- control program loader ------------------------------------------------
class IO:
    """Live view handed to control(). Reads pull from the datastore; writes to
    the actuator coils are pushed back after control() returns."""

    def __init__(self):
        hr = rd(3, 0, 20)
        co = rd(1, 0, 8)
        self.raw_level_pct = hr[M.HR_RAW_TANK_LEVEL_PCT_X100] / 100.0
        self.treated_level_pct = hr[M.HR_TREATED_TANK_LEVEL_PCT_X100] / 100.0
        self.chlorine_ppm = hr[M.HR_CHLORINE_PPM_X100] / 100.0
        self.dist_press_psi = hr[M.HR_DIST_PRESS_PSI_X100] / 100.0
        self.flow_gpm = hr[M.HR_FLOW_GPM_X10] / 10.0
        self.level_low_sp = hr[M.HR_LEVEL_LOW_SP_PCT]
        self.level_high_sp = hr[M.HR_LEVEL_HIGH_SP_PCT]
        self.dist_press_target = hr[M.HR_DIST_PRESS_TARGET_PSI]
        self.safe_max_ppm = M.SAFE_MAX_PPM
        self.intake_pump = bool(co[M.CO_INTAKE_PUMP])
        self.dist_pump = bool(co[M.CO_DIST_PUMP])
        self.dose_enable = bool(co[M.CO_DOSE_ENABLE])
        self.bypass_interlock = bool(co[M.CO_BYPASS_INTERLOCK])
        self.intake_hand = bool(co[M.CO_INTAKE_HAND])
        self.dist_hand = bool(co[M.CO_DIST_HAND])
        self.dose_hand = bool(co[M.CO_DOSE_HAND])

    def commit(self):
        wr(1, M.CO_INTAKE_PUMP, [int(self.intake_pump)])
        wr(1, M.CO_DIST_PUMP, [int(self.dist_pump)])
        wr(1, M.CO_DOSE_ENABLE, [int(self.dose_enable)])


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


# --- scan loop ------------------------------------------------------------
def scan_loop():
    scan = 0
    while True:
        t0 = time.time()
        try:
            if rd(1, M.CO_CPU_RUN)[0]:
                # command validation (only when the program is hardened)
                if not WRITE_OPEN:
                    sp = rd(3, M.HR_DOSE_SETPOINT_PPM_X100)[0]
                    clamped = max(0, min(sp, int(M.SAFE_MAX_PPM * 100)))
                    if clamped != sp:
                        wr(3, M.HR_DOSE_SETPOINT_PPM_X100, [clamped])
                    tgt = rd(3, M.HR_DIST_PRESS_TARGET_PSI)[0]
                    wr(3, M.HR_DIST_PRESS_TARGET_PSI, [max(40, min(tgt, 80))])
                    wr(1, M.CO_BYPASS_INTERLOCK, [0])  # bypass is not remotely settable

                io = IO()
                _active["mod"].control(io)
                io.commit()

                # derived discrete inputs
                wr(2, M.DI_LEVEL_LOW, [int(io.raw_level_pct <= io.level_low_sp)])
                wr(2, M.DI_LEVEL_HIGH, [int(io.raw_level_pct >= io.level_high_sp)])
                wr(2, M.DI_PRESS_LOW, [int(io.dist_press_psi < io.dist_press_target - 3)])
                wr(2, M.DI_OVERDOSE, [int(io.chlorine_ppm >= M.SAFE_MAX_PPM)])

            # operator-facing mirror (updates even in STOP)
            hr = rd(3, 0, 20)
            hb = hr[M.HR_SIM_HEARTBEAT]
            now = time.time()
            if hb != scan_loop.last_hb:
                scan_loop.last_hb = hb
                scan_loop.last_hb_change = now
            wr(2, M.DI_COMMS_FAULT, [int(now - scan_loop.last_hb_change > 5.0)])
            wr(4, M.IR_RAW_TANK_LEVEL_PCT_X100, [hr[M.HR_RAW_TANK_LEVEL_PCT_X100]])
            wr(4, M.IR_TREATED_TANK_LEVEL_PCT_X100, [hr[M.HR_TREATED_TANK_LEVEL_PCT_X100]])
            wr(4, M.IR_CHLORINE_PPM_X100, [hr[M.HR_CHLORINE_PPM_X100]])
            wr(4, M.IR_DIST_PRESS_PSI_X100, [hr[M.HR_DIST_PRESS_PSI_X100]])
            wr(4, M.IR_FLOW_GPM_X10, [hr[M.HR_FLOW_GPM_X10]])
            wr(4, M.IR_DOSE_SETPOINT_PPM_X100, [hr[M.HR_DOSE_SETPOINT_PPM_X100]])
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
<h1>OpenPLC Runtime &mdash; Cross Creek water plant</h1>
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
    co = rd(1, 0, 8)
    di = rd(2, 0, 8)
    ir = rd(4, 0, 8)
    hr = rd(3, 0, 20)
    return jsonify(
        cpu_run=bool(co[M.CO_CPU_RUN]),
        program=_active["name"],
        keyswitch="REMOTE" if WRITE_OPEN else "RUN",
        coils=dict(
            intake_pump=bool(co[M.CO_INTAKE_PUMP]),
            dist_pump=bool(co[M.CO_DIST_PUMP]),
            dose_enable=bool(co[M.CO_DOSE_ENABLE]),
            bypass_interlock=bool(co[M.CO_BYPASS_INTERLOCK]),
        ),
        status=dict(
            level_low=bool(di[M.DI_LEVEL_LOW]),
            level_high=bool(di[M.DI_LEVEL_HIGH]),
            press_low=bool(di[M.DI_PRESS_LOW]),
            overdose=bool(di[M.DI_OVERDOSE]),
            comms_fault=bool(di[M.DI_COMMS_FAULT]),
        ),
        pv=dict(
            raw_level_pct=ir[M.IR_RAW_TANK_LEVEL_PCT_X100] / 100.0,
            treated_level_pct=ir[M.IR_TREATED_TANK_LEVEL_PCT_X100] / 100.0,
            chlorine_ppm=ir[M.IR_CHLORINE_PPM_X100] / 100.0,
            header_psi=ir[M.IR_DIST_PRESS_PSI_X100] / 100.0,
            flow_gpm=ir[M.IR_FLOW_GPM_X10] / 10.0,
        ),
        sp=dict(
            dose_ppm=hr[M.HR_DOSE_SETPOINT_PPM_X100] / 100.0,
            press_target=hr[M.HR_DIST_PRESS_TARGET_PSI],
        ),
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
    # accept a python control() module; wrap a bare .st in a passthrough note
    if "def control(" not in data:
        return Response(
            "This runtime executes a control(io) module. Compile your ST first.\n",
            400,
        )
    with open(ACTIVE_PATH, "w") as out:
        out.write(data)
    reload_active()
    return Response(f"program accepted and running: {_active['name']}\n", 200)


# --- boot --------------------------------------------------------------
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
