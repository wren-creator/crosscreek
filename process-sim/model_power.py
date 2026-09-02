"""Lumped model of the Cross Creek substation bus.

Four numbers: bus frequency, bus voltage, served load, local generation. Each
step takes the breaker positions the RTU reports and advances the electrical
state. Coarse on purpose.

Steady state with all breakers closed: 50.00 Hz, 120 kV, 25 MW, grid-tied.
  * open the feeder breaker  -> the bus islands; frequency swings on the
    generation/load imbalance instead of being held by the grid
  * open the load breaker    -> load drops to near zero; islanded frequency
    runs high, grid-tied it barely moves
"""
from dataclasses import dataclass

FREQ_NOMINAL = 50.0
KV_NOMINAL = 120.0
LOAD_NOMINAL_MW = 25.0


@dataclass
class PowerState:
    freq_hz: float = 50.0
    voltage_kv: float = 120.0
    load_mw: float = 25.0
    gen_mw: float = 25.0

    def step(self, dt, *, feeder_closed, tie_closed, load_closed, gen_setpoint_mw):
        target_load = LOAD_NOMINAL_MW if load_closed else 0.4
        self.load_mw += (target_load - self.load_mw) * min(1.0, 2.0 * dt)
        self.gen_mw += (gen_setpoint_mw - self.gen_mw) * min(1.0, 0.5 * dt)
        imbalance = self.gen_mw - self.load_mw

        if feeder_closed:
            # grid holds frequency; small residual from local imbalance
            self.freq_hz += (FREQ_NOMINAL - self.freq_hz) * min(1.0, 1.5 * dt)
            self.freq_hz += 0.003 * imbalance * dt
        else:
            # islanded: nothing external holds it, frequency ramps on the
            # generation/load imbalance (slow enough to watch it happen)
            self.freq_hz += 0.045 * imbalance * dt
            self.freq_hz += (FREQ_NOMINAL - self.freq_hz) * 0.03 * dt  # weak governor
        self.freq_hz = max(45.0, min(self.freq_hz, 55.0))

        v_target = KV_NOMINAL - 0.18 * (self.load_mw - LOAD_NOMINAL_MW)
        if not feeder_closed:
            v_target -= 4.0
        self.voltage_kv += (v_target - self.voltage_kv) * min(1.0, dt)
        self.voltage_kv = max(90.0, min(self.voltage_kv, 140.0))
        return self
