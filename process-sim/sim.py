#!/usr/bin/env python3
"""process-sim: drives the physical model from the PLC outputs.

Two field loops:
  * water  -> plc-water over Modbus/TCP
  * power  -> plc-power over S7comm

The dosing controller (CIP) mirrors its setpoint through plc-water for now and
gets its own bridge in the dosing slice.
"""
import os
import socket
import struct
import threading
import time

import snap7
from flask import Flask, jsonify
from pymodbus.client import ModbusTcpClient

import s7map as S
import watermap as W
from model_power import PowerState
from model_water import WaterState

WATER_HOST = os.environ.get("PLC_WATER_HOST", "172.30.41.10")
WATER_PORT = int(os.environ.get("PLC_WATER_PORT", "502"))
POWER_HOST = os.environ.get("PLC_POWER_HOST", "172.30.41.12")
TICK = float(os.environ.get("TICK_SECONDS", "1.0"))

water = WaterState()
power = PowerState()
_hb = 0
_last_ok = {"water": 0.0, "power": 0.0}


# --- water -------------------------------------------------------------
def water_tick(client, dt):
    global _hb
    co = client.read_coils(0, 8, slave=1)
    hr = client.read_holding_registers(0, 20, slave=1)
    if co.isError() or hr.isError():
        return
    cpu_run = bool(co.bits[W.CO_CPU_RUN])
    water.step(
        dt,
        intake_pump=bool(co.bits[W.CO_INTAKE_PUMP]) and cpu_run,
        dist_pump=bool(co.bits[W.CO_DIST_PUMP]) and cpu_run,
        dose_enable=bool(co.bits[W.CO_DOSE_ENABLE]) and cpu_run,
        dose_setpoint_ppm=hr.registers[W.HR_DOSE_SETPOINT_PPM_X100] / 100.0,
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
    _last_ok["water"] = time.time()


def water_loop():
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


# --- power -------------------------------------------------------------
def power_tick(client, dt):
    db = client.db_read(S.DB_NUMBER, 0, S.DB_SIZE)
    status = db[S.BREAKER_STATUS]
    cpu_run = db[S.CPU_MODE] == 1
    gen_sp = struct.unpack_from(">h", db, S.GEN_SETPOINT_MW_X10)[0] / 10.0
    power.step(
        dt,
        feeder_closed=bool(status & (1 << S.BRK_FEEDER)),
        tie_closed=bool(status & (1 << S.BRK_TIE)),
        load_closed=bool(status & (1 << S.BRK_LOAD)),
        gen_setpoint_mw=gen_sp if cpu_run else power.gen_mw,
    )
    struct.pack_into(">h", db, S.BUS_FREQ_X100, int(power.freq_hz * 100))
    struct.pack_into(">h", db, S.BUS_VOLTAGE_KV_X10, int(power.voltage_kv * 10))
    struct.pack_into(">h", db, S.LOAD_MW_X10, int(power.load_mw * 10))
    client.db_write(S.DB_NUMBER, S.BUS_FREQ_X100,
                    db[S.BUS_FREQ_X100:S.BUS_FREQ_X100 + 6])
    _last_ok["power"] = time.time()


def power_loop():
    client = snap7.client.Client()
    while True:
        t0 = time.time()
        try:
            if not client.get_connected():
                # snap7's C client needs an IP, not a DNS name
                client.connect(socket.gethostbyname(POWER_HOST), 0, 1)
            power_tick(client, TICK)
        except Exception as exc:
            print(f"[process-sim] power fault: {exc}")
            try:
                client.disconnect()
            except Exception:
                pass
        time.sleep(max(0.0, TICK - (time.time() - t0)))


# --- status endpoint --------------------------------------------------
app = Flask(__name__)


@app.get("/health")
def health():
    fresh = (time.time() - _last_ok["water"]) < 10
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
        power=dict(
            freq_hz=round(power.freq_hz, 3),
            voltage_kv=round(power.voltage_kv, 1),
            load_mw=round(power.load_mw, 1),
            gen_mw=round(power.gen_mw, 1),
        ),
    )


def main():
    threading.Thread(target=water_loop, daemon=True).start()
    threading.Thread(target=power_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8099, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
