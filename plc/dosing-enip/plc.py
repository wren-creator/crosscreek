#!/usr/bin/env python3
"""plc-dosing: Cross Creek chlorine dosing controller (EtherNet/IP on :44818).

An embedded cpppo EtherNet/IP simulator carries the tags; a scan loop reads and
writes them directly; a Flask service on :8080 is the unauthenticated
logic-update stand-in (scenario 8).

Tags (all scalar):
  DoseSetpoint  REAL   chlorine residual target, ppm      (default 2.5)
  DoseRate      REAL   metering pump output, %            (computed)
  FlowFeedback  REAL   treatment flow, gpm                (written by process-sim)
  Mode          DINT   0 = PROG, 1 = RUN, 2 = REMOTE
  LogicRev      DINT   bumps every time a program is pushed
  LogicForced   DINT   0 = golden logic, 1 = pushed logic forcing max dose
"""
import os
import threading
import time

import cpppo.server.enip.main as enip
from flask import Flask, Response, jsonify, request

ALLOW_DL = os.environ.get("ENIP_ALLOW_LOGIC_DOWNLOAD", "1") == "1"
TAGS = ["DoseSetpoint=REAL", "DoseRate=REAL", "FlowFeedback=REAL",
        "Mode=DINT", "LogicRev=DINT", "LogicForced=DINT"]


def tag(name):
    return enip.tags[name]["attribute"]


def get(name):
    return tag(name)[0]


def put(name, value):
    tag(name)[0] = value


def scan_loop():
    while True:
        try:
            mode = get("Mode")
            sp = get("DoseSetpoint")
            forced = get("LogicForced")
            if mode == 0:                       # PROG: outputs frozen at 0
                put("DoseRate", 0.0)
            elif forced:                        # pushed logic: pump wide open
                put("DoseRate", 100.0)
            else:                               # golden logic: proportional trim
                flow = get("FlowFeedback")
                rate = 0.0 if flow < 1.0 else max(0.0, min(100.0, sp * 22.0))
                put("DoseRate", rate)
        except Exception as exc:
            print(f"[plc-dosing] scan fault: {exc}")
        time.sleep(0.2)


app = Flask(__name__)


@app.get("/health")
def health():
    return "ok", 200


@app.get("/api/state")
def api_state():
    return jsonify(
        mode={0: "PROG", 1: "RUN", 2: "REMOTE"}.get(get("Mode"), "?"),
        keyswitch="REMOTE" if ALLOW_DL else "RUN",
        logic_rev=get("LogicRev"),
        logic_forced=bool(get("LogicForced")),
        tags=dict(
            DoseSetpoint=round(get("DoseSetpoint"), 3),
            DoseRate=round(get("DoseRate"), 1),
            FlowFeedback=round(get("FlowFeedback"), 1),
        ),
    )


@app.post("/logic")
def logic_push():
    """Unauthenticated program download stand-in."""
    if not ALLOW_DL:
        return Response("Controller keyswitch is in RUN. Downloads disabled.\n", 403)
    payload = (request.get_data(as_text=True) or "").strip()
    put("LogicForced", 1)
    put("Mode", 1)  # drop it into RUN so the forced logic executes
    put("LogicRev", int(get("LogicRev")) + 1)
    name = payload[:40] or "unnamed_program"
    return Response(
        f"program accepted, rev {get('LogicRev')}: {name}\n"
        "metering pump forced to 100%, downstream interlock bypassed\n", 200)


def run_enip():
    enip.main(argv=["--address", "0.0.0.0:44818", *TAGS])


def main():
    threading.Thread(target=run_enip, daemon=True).start()
    time.sleep(3)  # let the tag store come up
    put("DoseSetpoint", 2.5)
    put("Mode", 2 if ALLOW_DL else 1)
    put("LogicRev", 1)
    put("LogicForced", 0)
    threading.Thread(target=scan_loop, daemon=True).start()
    print(f"[plc-dosing] EtherNet/IP on :44818, "
          f"keyswitch {'REMOTE' if ALLOW_DL else 'RUN'}")
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
