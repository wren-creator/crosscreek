"""Golden control program for the Cross Creek water plant.

OpenPLC-style: a single `control(io)` function that the scan loop calls every
cycle. `io` is a live view of the process. Set the outputs, return nothing.

This is the known-good logic. `./reset.sh` reloads it. Scenario 9 replaces the
running copy under /plc/logic/runtime/active.py with an attacker version that
strips the interlock.
"""

PROGRAM_NAME = "crosscreek_water_v1 (golden)"


def control(io):
    # --- raw water intake: level control with hysteresis ---------------------
    if io.raw_level_pct <= io.level_low_sp:
        io.intake_pump = True
    elif io.raw_level_pct >= io.level_high_sp:
        io.intake_pump = False
    # else: hold last state

    # High-level interlock. The tank physically overflows above 98%. Unless an
    # operator has thrown the bypass, the program force-stops the intake pump
    # here regardless of anything a remote client wrote to the coil.
    if io.raw_level_pct >= 98.0 and not io.bypass_interlock:
        io.intake_pump = False

    # --- chlorine dosing: dose only when water is actually moving ------------
    io.dose_enable = io.flow_gpm > 1.0

    # Overdose interlock: cut dosing hard if the residual runs away.
    if io.chlorine_ppm >= io.safe_max_ppm:
        io.dose_enable = False

    # --- distribution: hold header pressure in a band -----------------------
    if io.dist_press_psi < io.dist_press_target - 3:
        io.dist_pump = True
    elif io.dist_press_psi > io.dist_press_target + 3:
        io.dist_pump = False

    # Do not run the high-service pump against an empty clearwell.
    if io.treated_level_pct < 10.0:
        io.dist_pump = False
