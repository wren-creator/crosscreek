#!/usr/bin/env python3
"""plc-power: Cross Creek substation RTU (S7comm on :102).

python-snap7 server exposing DB1 (bus values, breaker status, breaker commands).
A scan loop acts on breaker commands and mirrors the virtual CPU run/stop state
into DB1.CPU_MODE for the HMI.

S7_NO_PASSWORD=1 (default): a client can stop the CPU or open a breaker with no
authentication (scenario 7). S7_NO_PASSWORD=0: the scan loop forces the CPU
back to RUN and ignores breaker-open commands unless DB1.AUTH_OK == 1.
"""
import ctypes
import os
import struct
import threading
import time

from flask import Flask, jsonify
from snap7.server import Server
from snap7.type import SrvArea

import s7map as S

NO_PASSWORD = os.environ.get("S7_NO_PASSWORD", "1") == "1"
CPU_RUN, CPU_STOP = 8, 4

DB = (ctypes.c_uint8 * S.DB_SIZE)()
SRV = Server()


def _i16(off):
    return struct.unpack_from(">h", DB, off)[0]


def _set_i16(off, val):
    struct.pack_into(">h", DB, off, int(val))


def _seed():
    _set_i16(S.BUS_FREQ_X100, 5000)
    _set_i16(S.BUS_VOLTAGE_KV_X10, 1200)
    _set_i16(S.LOAD_MW_X10, 250)
    _set_i16(S.GEN_SETPOINT_MW_X10, 250)
    DB[S.BREAKER_STATUS] = 0b111
    DB[S.BREAKER_CMD] = 0
    DB[S.CPU_MODE] = 1
    DB[S.AUTH_OK] = 0


def scan_loop():
    scan = 0
    while True:
        try:
            hardened = not NO_PASSWORD
            authed = DB[S.AUTH_OK] == 1
            _, cpu_status, _ = SRV.get_status()

            # a hardened RTU will not stay stopped for an unauthenticated client
            if hardened and not authed and cpu_status == "S7CpuStatusStop":
                SRV.set_cpu_status(CPU_RUN)
                cpu_status = "S7CpuStatusRun"
            DB[S.CPU_MODE] = 1 if cpu_status == "S7CpuStatusRun" else 0

            if DB[S.CPU_MODE] == 1 and DB[S.BREAKER_CMD]:
                cmd = DB[S.BREAKER_CMD]
                status = DB[S.BREAKER_STATUS]
                allow_open = (not hardened) or authed
                for close_bit, open_bit, brk in (
                    (S.CMD_FEEDER_CLOSE, S.CMD_FEEDER_OPEN, S.BRK_FEEDER),
                    (S.CMD_TIE_CLOSE, S.CMD_TIE_OPEN, S.BRK_TIE),
                    (S.CMD_LOAD_CLOSE, S.CMD_LOAD_OPEN, S.BRK_LOAD),
                ):
                    if cmd & (1 << close_bit):
                        status |= (1 << brk)
                    if cmd & (1 << open_bit) and allow_open:
                        status &= ~(1 << brk)
                DB[S.BREAKER_STATUS] = status & 0xFF
                DB[S.BREAKER_CMD] = 0

            scan = (scan + 1) & 0x7FFF
            _set_i16(S.SCAN_COUNT, scan)
        except Exception as exc:
            print(f"[plc-power] scan fault: {exc}")
        time.sleep(0.2)


app = Flask(__name__)


@app.get("/health")
def health():
    return "ok", 200


@app.get("/api/state")
def api_state():
    st = DB[S.BREAKER_STATUS]
    return jsonify(
        cpu_mode="RUN" if DB[S.CPU_MODE] == 1 else "STOP",
        auth_ok=bool(DB[S.AUTH_OK]),
        breakers=dict(
            feeder=bool(st & (1 << S.BRK_FEEDER)),
            bus_tie=bool(st & (1 << S.BRK_TIE)),
            load=bool(st & (1 << S.BRK_LOAD)),
        ),
        pv=dict(
            freq_hz=_i16(S.BUS_FREQ_X100) / 100.0,
            voltage_kv=_i16(S.BUS_VOLTAGE_KV_X10) / 10.0,
            load_mw=_i16(S.LOAD_MW_X10) / 10.0,
        ),
        sp=dict(gen_mw=_i16(S.GEN_SETPOINT_MW_X10) / 10.0),
        scan=_i16(S.SCAN_COUNT),
    )


def main():
    _seed()
    SRV.register_area(SrvArea.DB, S.DB_NUMBER, DB)
    SRV.start()  # default TCP 102
    SRV.set_cpu_status(CPU_RUN)
    print(f"[plc-power] S7comm on :102, DB{S.DB_NUMBER} ({S.DB_SIZE} bytes), "
          f"{'no-password' if NO_PASSWORD else 'auth required'}")
    threading.Thread(target=scan_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
