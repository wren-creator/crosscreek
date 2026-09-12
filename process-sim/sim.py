#!/usr/bin/env python3
"""process-sim: drives the physical model from the PLC outputs.

Three field loops:
  * water   -> plc-water over Modbus/TCP  (RO demineralisation plant)
  * power   -> plc-power over S7comm      (substation bus)
  * dosing  -> plc-dosing over EtherNet/IP (CIP)  (NaOH inter-pass dosing)

The dosing loop reads the metering rate and logic state from the CIP controller
and feeds the RO model, so tampering with the water PLC's setpoints, the CIP
metering rate, or the CIP control logic all show up as conductivity.
"""
import os
import socket
import struct
import threading
import time

import snap7
from cpppo.server.enip import client as enip_client
from flask import Flask, jsonify
from pymodbus.client import ModbusTcpClient

import s7map as S
import watermap as W
from model_power import PowerState
from model_water import RoWaterState

WATER_HOST = os.environ.get("PLC_WATER_HOST", "172.30.41.10")
WATER_PORT = int(os.environ.get("PLC_WATER_PORT", "10502"))
POWER_HOST = os.environ.get("PLC_POWER_HOST", "172.30.41.12")
POWER_PORT = int(os.environ.get("PLC_POWER_PORT", "10102"))
DOSING_HOST = os.environ.get("PLC_DOSING_HOST", "172.30.41.11")
DOSING_PORT = int(os.environ.get("PLC_DOSING_PORT", "54818"))
TICK = float(os.environ.get("TICK_SECONDS", "1.0"))

water = RoWaterState()
power = PowerState()
_hb = 0
_last_ok = {"water": 0.0, "power": 0.0, "dosing": 0.0}
# NaOH dose commanded by the CIP controller: L/h and whether the logic is forced
_dose = {"naoh_lh": 4.0, "forced": False, "rev": 1}


# --- water: RO plant over Modbus ------------------------------------------
def water_tick(client, dt):
    global _hb
    co = client.read_coils(0, 24, slave=1)
    hr = client.read_holding_registers(0, 24, slave=1)
    if co.isError() or hr.isError():
        return
    b = co.bits
    loop_press_sp = hr.registers[W.HR_LOOP_PRESS_SP_BAR_X100] / 100.0
    antiscalant_rate = hr.registers[W.HR_ANTISCALANT_RATE_LH_X10] / 10.0
    # the CIP controller owns the NaOH rate; fall back to the PLC setpoint
    naoh_rate = _dose["naoh_lh"] if _last_ok["dosing"] else \
        hr.registers[W.HR_NAOH_RATE_LH_X10] / 10.0

    water.step(
        dt,
        p102_feed=bool(b[W.CO_P102_FEED]),
        p101_antiscalant=bool(b[W.CO_P101_ANTISCALANT]),
        p301_ro1=bool(b[W.CO_P301_RO1_HP]),
        p302_ro2=bool(b[W.CO_P302_RO2]),
        p401_loop=bool(b[W.CO_P401_LOOP]),
        uv401=bool(b[W.CO_UV401]),
        seq_cip=bool(b[W.CO_SEQ_CIP]) or bool(b[W.CO_SEQ_SANITISE]),
        abnahme=bool(b[W.CO_ABNAHME]),
        loop_press_sp=loop_press_sp,
        antiscalant_rate_lh=antiscalant_rate,
        naoh_rate_lh=naoh_rate,
        contaminant_us=4.0 if _dose["forced"] else 0.0,
    )

    _hb = (_hb + 1) & 0xFFFF
    client.write_registers(
        W.HR_FEED_FLOW_M3H_X100,
        [
            int(water.feed_flow_m3h * 100),
            int(water.feed_press_bar * 100),
            int(water.ro1_cond_us * 100),
            int(water.ro2_cond_us * 100),
            int(water.ro2_press_bar * 100),
            int(water.ro_recovery_pct * 100),
            int(water.di_tank_pct * 100),
            int(water.loop_press_bar * 100),
            int(water.loop_flow_m3h * 100),
            int(water.loop_ret_cond_us * 100),
            int(water.antiscalant_tank_pct * 100),
            int(water.naoh_tank_pct * 100),
            int(water.uv_intensity_pct * 100),
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


# --- dosing (CIP): NaOH inter-pass metering ------------------------------
def dosing_loop():
    ip = socket.gethostbyname(DOSING_HOST)
    while True:
        t0 = time.time()
        try:
            with enip_client.connector(host=ip, port=DOSING_PORT, timeout=3) as conn:
                ops = enip_client.parse_operations([
                    f"FlowFeedback=(REAL){water.feed_flow_m3h}",
                    "DoseRate", "LogicForced", "LogicRev",
                ])
                results = list(conn.pipeline(operations=ops, depth=1))
            vals = [val for _, _, _, _, sts, val in results]
            rate_pct = float(vals[1][0])            # metering-pump output %
            _dose["naoh_lh"] = rate_pct / 100.0 * 8.0
            _dose["forced"] = bool(vals[2][0])
            _dose["rev"] = int(vals[3][0])
            _last_ok["dosing"] = time.time()
        except Exception as exc:
            print(f"[process-sim] dosing fault: {exc}")
        time.sleep(max(0.0, TICK - (time.time() - t0)))


# --- power (S7) ----------------------------------------------------
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
                client.connect(socket.gethostbyname(POWER_HOST), 0, 1, POWER_PORT)
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
            feed_flow_m3h=round(water.feed_flow_m3h, 2),
            ro1_cond_us=round(water.ro1_cond_us, 2),
            ro2_cond_us=round(water.ro2_cond_us, 3),
            ro_recovery_pct=round(water.ro_recovery_pct, 1),
            di_tank_pct=round(water.di_tank_pct, 1),
            loop_press_bar=round(water.loop_press_bar, 2),
            loop_ret_cond_us=round(water.loop_ret_cond_us, 3),
            uv_intensity_pct=round(water.uv_intensity_pct, 1),
            fouling=round(water.fouling, 3),
        ),
        dosing=dict(
            naoh_lh=round(_dose["naoh_lh"], 2),
            logic_forced=_dose["forced"],
            logic_rev=_dose["rev"],
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
    threading.Thread(target=dosing_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8099, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
