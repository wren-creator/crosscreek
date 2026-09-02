"""Cross Creek water plant Modbus map (slave id 1, zero-based addresses).

This is the wire contract shared by plc-water, process-sim and hmi-water.
Everything is 16-bit. Physical values are scaled to fit an integer register:
_X100 means the real value is register / 100.0.

Coils (FC 1 read, FC 5/15 write) -- actuator commands and CPU state
    0  CO_INTAKE_PUMP        raw-water intake pump run command
    1  CO_DIST_PUMP          distribution / high-service pump run command
    2  CO_DOSE_ENABLE        chlorine dosing enable
    3  CO_CPU_RUN            1 = program executing (soft keyswitch RUN), 0 = STOP
    4  CO_BYPASS_INTERLOCK   operator bypass of the high-level interlock
    5  CO_INTAKE_HAND        1 = intake pump in HAND, program leaves it to the operator
    6  CO_DIST_HAND          1 = distribution pump in HAND
    7  CO_DOSE_HAND          1 = dosing in HAND

Discrete inputs (FC 2 read) -- derived status
    0  DI_LEVEL_LOW          raw tank below low setpoint
    1  DI_LEVEL_HIGH         raw tank above high setpoint
    2  DI_PRESS_LOW          distribution header below target band
    3  DI_OVERDOSE           chlorine above safe maximum
    4  DI_COMMS_FAULT        process-sim heartbeat stale

Holding registers (FC 3 read, FC 6/16 write) -- setpoints + field I/O
    0  HR_DOSE_SETPOINT_PPM_X100     chlorine dose target, x100
    1  HR_DIST_PRESS_TARGET_PSI      distribution header target
    2  HR_LEVEL_LOW_SP_PCT           raw tank low setpoint %
    3  HR_LEVEL_HIGH_SP_PCT          raw tank high setpoint %
    -- field I/O block: process-sim writes these every tick --
    10 HR_RAW_TANK_LEVEL_PCT_X100
    11 HR_TREATED_TANK_LEVEL_PCT_X100
    12 HR_CHLORINE_PPM_X100
    13 HR_DIST_PRESS_PSI_X100
    14 HR_FLOW_GPM_X10
    15 HR_SIM_HEARTBEAT              free-running counter from process-sim

Input registers (FC 4 read) -- operator-facing mirror, written by the scan loop
    0  IR_RAW_TANK_LEVEL_PCT_X100
    1  IR_TREATED_TANK_LEVEL_PCT_X100
    2  IR_CHLORINE_PPM_X100
    3  IR_DIST_PRESS_PSI_X100
    4  IR_FLOW_GPM_X10
    5  IR_DOSE_SETPOINT_PPM_X100     echo of HR 0 as the program sees it
    6  IR_CPU_SCAN_COUNT
"""

# coils
CO_INTAKE_PUMP = 0
CO_DIST_PUMP = 1
CO_DOSE_ENABLE = 2
CO_CPU_RUN = 3
CO_BYPASS_INTERLOCK = 4
CO_INTAKE_HAND = 5     # 1 = operator has taken this pump to HAND (manual)
CO_DIST_HAND = 6
CO_DOSE_HAND = 7

# discrete inputs
DI_LEVEL_LOW = 0
DI_LEVEL_HIGH = 1
DI_PRESS_LOW = 2
DI_OVERDOSE = 3
DI_COMMS_FAULT = 4

# holding registers
HR_DOSE_SETPOINT_PPM_X100 = 0
HR_DIST_PRESS_TARGET_PSI = 1
HR_LEVEL_LOW_SP_PCT = 2
HR_LEVEL_HIGH_SP_PCT = 3
HR_RAW_TANK_LEVEL_PCT_X100 = 10
HR_TREATED_TANK_LEVEL_PCT_X100 = 11
HR_CHLORINE_PPM_X100 = 12
HR_DIST_PRESS_PSI_X100 = 13
HR_FLOW_GPM_X10 = 14
HR_SIM_HEARTBEAT = 15

# input registers
IR_RAW_TANK_LEVEL_PCT_X100 = 0
IR_TREATED_TANK_LEVEL_PCT_X100 = 1
IR_CHLORINE_PPM_X100 = 2
IR_DIST_PRESS_PSI_X100 = 3
IR_FLOW_GPM_X10 = 4
IR_DOSE_SETPOINT_PPM_X100 = 5
IR_CPU_SCAN_COUNT = 6

# plant constants
SAFE_MAX_PPM = 4.0            # anything above this is an overdose
DESIGN_PPM = 2.5             # normal chlorine residual target
DEFAULT_LOW_SP_PCT = 35
DEFAULT_HIGH_SP_PCT = 85
DEFAULT_PRESS_TARGET_PSI = 60
