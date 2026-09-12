#!/usr/bin/env python3
"""historian: poll OT, record to sqlite, serve the recent history.

HISTORIAN_READONLY=1 (Session 6): the poller opens read-only protocol clients
and the process holds no code path that writes to a PLC. In the flat default
(=0) the same bidirectional client object is reused, which is what makes the
historian a viable pivot back into OT.
"""
import os
import socket
import sqlite3
import struct
import threading
import time

import snap7
from flask import Flask, jsonify
from pymodbus.client import ModbusTcpClient

READONLY = os.environ.get("HISTORIAN_READONLY", "0") == "1"
MB_HOST, MB_PORT = os.environ.get("POLL_MODBUS", "172.30.40.20:10502").split(":")
S7_HOST, S7_PORT = os.environ.get("POLL_S7", "172.30.40.22:10102").split(":")
DB = "/var/lib/historian/history.db"

_conn = sqlite3.connect(DB, check_same_thread=False)
_conn.execute("CREATE TABLE IF NOT EXISTS samples "
              "(ts REAL, tag TEXT, value REAL)")
_conn.commit()
_lock = threading.Lock()
_last_ok = 0.0


def record(rows):
    with _lock:
        _conn.executemany("INSERT INTO samples VALUES (?,?,?)", rows)
        _conn.commit()


def poll_loop():
    global _last_ok
    mb = ModbusTcpClient(MB_HOST, port=int(MB_PORT), timeout=2)
    s7 = snap7.client.Client()
    while True:
        now = time.time()
        rows = []
        try:
            if not mb.connected:
                mb.connect()
            ir = mb.read_input_registers(0, 16, slave=1)
            if not ir.isError():
                # RO plant input registers: 3 = RO2 conductivity, 6 = DI tank,
                # 7 = loop pressure (see plc-water/mapfile.py)
                rows += [
                    (now, "water.ro2_cond_us", ir.registers[3] / 100.0),
                    (now, "water.di_tank_pct", ir.registers[6] / 100.0),
                    (now, "water.loop_press_bar", ir.registers[7] / 100.0),
                ]
        except Exception as exc:
            print(f"[historian] modbus poll: {exc}")
        try:
            if not s7.get_connected():
                s7.connect(socket.gethostbyname(S7_HOST), 0, 1, int(S7_PORT))
            db = s7.db_read(1, 0, 8)
            rows += [
                (now, "power.freq_hz", struct.unpack_from(">h", db, 0)[0] / 100.0),
                (now, "power.load_mw", struct.unpack_from(">h", db, 4)[0] / 10.0),
            ]
        except Exception as exc:
            print(f"[historian] s7 poll: {exc}")
        if rows:
            record(rows)
            _last_ok = now
        time.sleep(5)


app = Flask(__name__)


@app.get("/health")
def health():
    return ("ok", 200) if (time.time() - _last_ok) < 30 else ("stale", 503)


@app.get("/recent")
def recent():
    with _lock:
        cur = _conn.execute(
            "SELECT ts, tag, value FROM samples ORDER BY ts DESC LIMIT 60")
        rows = [{"ts": r[0], "tag": r[1], "value": r[2]} for r in cur]
    return jsonify(mode="read-only" if READONLY else "read-write", samples=rows)


def main():
    print(f"[historian] polling {MB_HOST}:{MB_PORT} (Modbus) and "
          f"{S7_HOST}:{S7_PORT} (S7), mode="
          f"{'read-only' if READONLY else 'read-write'}")
    threading.Thread(target=poll_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8086, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
