"""Cross Creek substation RTU, S7 DB1 layout.

Shared contract for plc-power, process-sim and hmi-power. All multi-byte values
are big-endian signed 16-bit (S7 INT). Scaled to integers: a trailing _X100 means the
real value is the register / 100.

DB1, 24 bytes:
    off 0  INT   BUS_FREQ_X100          bus frequency, 5000 = 50.00 Hz
    off 2  INT   BUS_VOLTAGE_KV_X10     bus voltage,   1200  = 120.0 kV
    off 4  INT   LOAD_MW_X10            served load,   250   = 25.0 MW
    off 6  BYTE  BREAKER_STATUS         bit0 feeder  bit1 bus-tie  bit2 load  (1 = closed)
    off 7  BYTE  BREAKER_CMD            bit0 feeder_close  bit1 feeder_open
                                        bit2 tie_close     bit3 tie_open
                                        bit4 load_close    bit5 load_open
    off 8  BYTE  CPU_MODE              0 = STOP, 1 = RUN
    off 9  BYTE  AUTH_OK              client sets 1 after authenticating (segmented)
    off 10 INT   GEN_SETPOINT_MW_X10  local generation setpoint
    off 12 INT   SCAN_COUNT
"""
DB_NUMBER = 1
DB_SIZE = 24

BUS_FREQ_X100 = 0
BUS_VOLTAGE_KV_X10 = 2
LOAD_MW_X10 = 4
BREAKER_STATUS = 6
BREAKER_CMD = 7
CPU_MODE = 8
AUTH_OK = 9
GEN_SETPOINT_MW_X10 = 10
SCAN_COUNT = 12

# breaker bit positions
BRK_FEEDER = 0
BRK_TIE = 1
BRK_LOAD = 2

# command bit positions
CMD_FEEDER_CLOSE = 0
CMD_FEEDER_OPEN = 1
CMD_TIE_CLOSE = 2
CMD_TIE_OPEN = 3
CMD_LOAD_CLOSE = 4
CMD_LOAD_OPEN = 5

NOMINAL_FREQ_HZ = 50.0
NOMINAL_KV = 120.0
NOMINAL_LOAD_MW = 25.0
