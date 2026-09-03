"""Cross Creek water plant Modbus map (slave id 1, zero-based addresses).

The water side is a two-pass reverse-osmosis demineralisation plant with a
recirculating DI (deionised / "VE-Wasser") distribution loop, modelled on a
real Siemens SIMATIC-panelled Reinstwasser plant. Tag prefixes follow the
panel: 1xxx = feed / pretreatment, 2xxx = RO, 3xxx = DI loop.

This is the wire contract shared by plc-water, process-sim and hmi-water.
Everything is 16-bit. `_X100` means the real value is register / 100.

Coils (FC 1 read, FC 5/15 write)
    0  CO_P101_ANTISCALANT    1P101 antiscalant metering pump
    1  CO_P102_FEED           1P102 RO feed pump
    2  CO_P301_RO1_HP         2P301 RO pass-1 high-pressure pump
    3  CO_P302_RO2            2P302 RO pass-2 pump
    4  CO_P401_LOOP           3P401 DI loop circulation pump
    5  CO_UV401              3UV401 loop UV steriliser
    6  CO_CPU_RUN           1 = program executing (soft keyswitch RUN), 0 = STOP
    7  CO_ABNAHME           draw-off active: downstream users are drawing DI water
    8  CO_FREIGABE          release to consumers (set by the release interlock)
    9  CO_P101_HAND         per-device AUTO(0) / HAND(1)
    10 CO_P102_HAND
    11 CO_P301_HAND
    12 CO_P302_HAND
    13 CO_P401_HAND
    14 CO_UV_HAND
    15 CO_RO_VALVES_HAND     "RO Ventile" block in HAND (RO makeup no longer auto)
    16 CO_LOOP_VALVES_HAND   "LOOP Ventile" block in HAND
    17 CO_SEQ_RO             RO production sequence running
    18 CO_SEQ_LOOP           loop circulation sequence running
    19 CO_SEQ_CIP            clean-in-place running (RO train offline)
    20 CO_SEQ_SANITISE       hot/chemical sanitisation running
    21 CO_BYPASS_RELEASE_ILK bypass the conductivity release interlock (dangerous)

Discrete inputs (FC 2 read)
    0  DI_TANK_LOW           3B401 below low setpoint
    1  DI_TANK_HIGH          3B401 above high setpoint
    2  DI_LOOP_PRESS_LOW     3PITC401 below the control band
    3  DI_COND_HIGH_RO2      2QAH401 above the release limit (product off-spec)
    4  DI_COND_HIGH_LOOP     loop return conductivity above the release limit
    5  DI_UV_FAULT           3UV401 intensity below the disinfection threshold
    6  DI_FEED_FLOW_LOW      1FQIAHL101 low
    7  DI_ANTISCALANT_LOW    antiscalant tank low
    8  DI_NAOH_LOW           NaOH tank low
    9  DI_COMMS_FAULT        process-sim heartbeat stale
    10 DI_RELEASE_BLOCKED    the Freigabe interlock is holding release OFF

Holding registers (FC 3 read, FC 6/16 write)
    -- setpoints --
    0  HR_LOOP_PRESS_SP_BAR_X100     3PITC401 setpoint, default 380 (3.80 bar)
    1  HR_TANK_LO_SP_PCT             RO makeup starts below this, default 40
    2  HR_TANK_HI_SP_PCT             RO makeup stops above this, default 85
    3  HR_ANTISCALANT_RATE_LH_X10   antiscalant dose rate, default 25 (2.5 L/h)
    4  HR_NAOH_RATE_LH_X10          NaOH inter-pass dose rate, default 30 (3.0 L/h)
    5  HR_COND_LIMIT_US_X100        release conductivity limit, default 200 (2.00 uS/cm)
    6  HR_RO_RECOVERY_SP_PCT        target RO recovery, default 75
    -- field I/O block: process-sim writes these every tick --
    10 HR_FEED_FLOW_M3H_X100        1FQIAHL101
    11 HR_FEED_PRESS_BAR_X100       1PT105
    12 HR_RO1_COND_US_X100          1QAH301
    13 HR_RO2_COND_US_X100          2QAH401
    14 HR_RO2_PRESS_BAR_X100        2PT301
    15 HR_RO_RECOVERY_PCT_X100      Ausbeute RO
    16 HR_DI_TANK_PCT_X100          3B401
    17 HR_LOOP_PRESS_BAR_X100       3PITC401 PV
    18 HR_LOOP_FLOW_M3H_X100
    19 HR_LOOP_RET_COND_US_X100
    20 HR_ANTISCALANT_TANK_PCT_X100
    21 HR_NAOH_TANK_PCT_X100
    22 HR_UV_INTENSITY_PCT_X100
    23 HR_SIM_HEARTBEAT             free-running counter from process-sim

Input registers (FC 4 read) -- operator-facing mirror, written by the scan loop
    0  IR_FEED_FLOW_M3H_X100
    1  IR_FEED_PRESS_BAR_X100
    2  IR_RO1_COND_US_X100
    3  IR_RO2_COND_US_X100
    4  IR_RO2_PRESS_BAR_X100
    5  IR_RO_RECOVERY_PCT_X100
    6  IR_DI_TANK_PCT_X100
    7  IR_LOOP_PRESS_BAR_X100
    8  IR_LOOP_FLOW_M3H_X100
    9  IR_LOOP_RET_COND_US_X100
    10 IR_ANTISCALANT_TANK_PCT_X100
    11 IR_NAOH_TANK_PCT_X100
    12 IR_UV_INTENSITY_PCT_X100
    13 IR_LOOP_PRESS_SP_BAR_X100    echo of HR 0
    14 IR_COND_LIMIT_US_X100        echo of HR 5
    15 IR_CPU_SCAN_COUNT
"""

# --- coils ---
CO_P101_ANTISCALANT = 0
CO_P102_FEED = 1
CO_P301_RO1_HP = 2
CO_P302_RO2 = 3
CO_P401_LOOP = 4
CO_UV401 = 5
CO_CPU_RUN = 6
CO_ABNAHME = 7
CO_FREIGABE = 8
CO_P101_HAND = 9
CO_P102_HAND = 10
CO_P301_HAND = 11
CO_P302_HAND = 12
CO_P401_HAND = 13
CO_UV_HAND = 14
CO_RO_VALVES_HAND = 15
CO_LOOP_VALVES_HAND = 16
CO_SEQ_RO = 17
CO_SEQ_LOOP = 18
CO_SEQ_CIP = 19
CO_SEQ_SANITISE = 20
CO_BYPASS_RELEASE_ILK = 21

# per-device HAND coils, keyed by the short device name used in the HMI/API
HAND_COIL = {
    "P101": CO_P101_HAND, "P102": CO_P102_HAND, "P301": CO_P301_HAND,
    "P302": CO_P302_HAND, "P401": CO_P401_HAND, "UV": CO_UV_HAND,
    "RO_VALVES": CO_RO_VALVES_HAND, "LOOP_VALVES": CO_LOOP_VALVES_HAND,
}
RUN_COIL = {
    "P101": CO_P101_ANTISCALANT, "P102": CO_P102_FEED, "P301": CO_P301_RO1_HP,
    "P302": CO_P302_RO2, "P401": CO_P401_LOOP, "UV": CO_UV401,
}
SEQ_COIL = {
    "RO": CO_SEQ_RO, "LOOP": CO_SEQ_LOOP, "CIP": CO_SEQ_CIP,
    "SANITISE": CO_SEQ_SANITISE,
}

# --- discrete inputs ---
DI_TANK_LOW = 0
DI_TANK_HIGH = 1
DI_LOOP_PRESS_LOW = 2
DI_COND_HIGH_RO2 = 3
DI_COND_HIGH_LOOP = 4
DI_UV_FAULT = 5
DI_FEED_FLOW_LOW = 6
DI_ANTISCALANT_LOW = 7
DI_NAOH_LOW = 8
DI_COMMS_FAULT = 9
DI_RELEASE_BLOCKED = 10

# --- holding registers: setpoints ---
HR_LOOP_PRESS_SP_BAR_X100 = 0
HR_TANK_LO_SP_PCT = 1
HR_TANK_HI_SP_PCT = 2
HR_ANTISCALANT_RATE_LH_X10 = 3
HR_NAOH_RATE_LH_X10 = 4
HR_COND_LIMIT_US_X100 = 5
HR_RO_RECOVERY_SP_PCT = 6
SETPOINT_HR = {
    "loop_press": HR_LOOP_PRESS_SP_BAR_X100, "tank_lo": HR_TANK_LO_SP_PCT,
    "tank_hi": HR_TANK_HI_SP_PCT, "antiscalant_rate": HR_ANTISCALANT_RATE_LH_X10,
    "naoh_rate": HR_NAOH_RATE_LH_X10, "cond_limit": HR_COND_LIMIT_US_X100,
    "ro_recovery": HR_RO_RECOVERY_SP_PCT,
}

# --- holding registers: field I/O ---
HR_FEED_FLOW_M3H_X100 = 10
HR_FEED_PRESS_BAR_X100 = 11
HR_RO1_COND_US_X100 = 12
HR_RO2_COND_US_X100 = 13
HR_RO2_PRESS_BAR_X100 = 14
HR_RO_RECOVERY_PCT_X100 = 15
HR_DI_TANK_PCT_X100 = 16
HR_LOOP_PRESS_BAR_X100 = 17
HR_LOOP_FLOW_M3H_X100 = 18
HR_LOOP_RET_COND_US_X100 = 19
HR_ANTISCALANT_TANK_PCT_X100 = 20
HR_NAOH_TANK_PCT_X100 = 21
HR_UV_INTENSITY_PCT_X100 = 22
HR_SIM_HEARTBEAT = 23

# --- input registers ---
IR_FEED_FLOW_M3H_X100 = 0
IR_FEED_PRESS_BAR_X100 = 1
IR_RO1_COND_US_X100 = 2
IR_RO2_COND_US_X100 = 3
IR_RO2_PRESS_BAR_X100 = 4
IR_RO_RECOVERY_PCT_X100 = 5
IR_DI_TANK_PCT_X100 = 6
IR_LOOP_PRESS_BAR_X100 = 7
IR_LOOP_FLOW_M3H_X100 = 8
IR_LOOP_RET_COND_US_X100 = 9
IR_ANTISCALANT_TANK_PCT_X100 = 10
IR_NAOH_TANK_PCT_X100 = 11
IR_UV_INTENSITY_PCT_X100 = 12
IR_LOOP_PRESS_SP_BAR_X100 = 13
IR_COND_LIMIT_US_X100 = 14
IR_CPU_SCAN_COUNT = 15

# --- plant constants ---
COND_LIMIT_DEFAULT_US = 2.00       # DI water is released only below this
COND_ALARM_HARD_US = 10.0          # grossly off-spec: hard-stop RO pass 2
UV_MIN_INTENSITY_PCT = 70.0        # below this the loop is not disinfected
DEFAULT_LOOP_PRESS_BAR = 3.80
DEFAULT_TANK_LO_PCT = 40
DEFAULT_TANK_HI_PCT = 85
DEFAULT_ANTISCALANT_LH = 2.5
DEFAULT_NAOH_LH = 3.0
DEFAULT_RO_RECOVERY_PCT = 75
