#!/usr/bin/env python3
"""process-sim: drives the physical model from the PLC outputs.

For this slice it talks to plc-water over Modbus/TCP. The dosing controller
(CIP) and the substation RTU (S7) are wired in a later slice; their models are
already here and tick on internal defaults until then.
"""
import os
import threading
import time

from flask import Flask, jsonify
from pymodbus.client import ModbusTcpClient

import watermap as W
from model_water import WaterState

WATER_HOST = os.environ.get("PLC_WATER_HOST", "172.30.41.10")
WATER_PORT = int(os.environ.get("PLC_WATER_PORT", "502"))
TICK = float(os.environ.get("TICK_SECONDS", "1.0"))

water = WaterState()
_hb = 0
_last_ok = 0.0


def water_tick(client, dt):
    global _hb, _last_ok
    co = client.read_coils(0, 8, slave=1)
    hr = client.read_holding_registers(0, 20, slave=1)
    if co.isError() or hr.isError():
        return
    intake = bool(co.bits[W.CO_INTAKE_PUMP])
    dist = bool(co.bits[W.CO_DIST_PUMP])
    dose = bool(co.bits[W.CO_DOSE_ENABLE])
    cpu_run = bool(co.bits[W.CO_CPU_RUN])
    dose_sp = hr.registers[W.HR_DOSE_SETPOINT_PPM_X100] / 100.0

    # if the CPU is in STOP the outputs freeze wherever they were
    water.step(
        dt,
        intake_pump=intake and cpu_run,
        dist_pump=dist and cpu_run,
        dose_enable=dose and cpu_run,
        dose_setpoint_ppm=dose_sp,
    )

    _hb = (_hb + 1) & 0xFFFF
    client.write_registers(
        W.HR_RAW_TANK_LEVEL_PCT_X100,
        [
            int(water.raw_level_pct * 100),
            int(water.treated_level_pct * 100),
            int(water.chlorine_ppm * 100),
            int(water.header_psi * 100),
            int(water.flow_gpm * 10),
            _hb,
        ],
        slave=1,
    )
    _last_ok = time.time()


def loop():
    client = ModbusTcpClient(WATER_HOST, port=WATER_PORT, timeout=2)
    while True:
        t0 = time.time()
        try:
            if not client.connected:
                client.connect()
            water_tick(client, TICK)
        except Exception as exc:
            print(f"[process-sim] water fault: {exc}")
        time.sleep(max(0.0, TICK - (time.time() - t0)))


app = Flask(__name__)


@app.get("/health")
def health():
    fresh = (time.time() - _last_ok) < 10
    return ("ok", 200) if fresh else ("stale", 503)


@app.get("/state")
def state():
    return jsonify(
        heartbeat=_hb,
        water=dict(
            raw_level_pct=round(water.raw_level_pct, 2),
            treated_level_pct=round(water.treated_level_pct, 2),
            chlorine_ppm=round(water.chlorine_ppm, 3),
            header_psi=round(water.header_psi, 2),
            flow_gpm=round(water.flow_gpm, 1),
        ),
    )


def main():
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8099, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
