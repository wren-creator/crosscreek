"""Lumped model of the Cross Creek water plant.

State is five numbers. Each step takes the actuator commands the PLC set and
advances the physical values by `dt` seconds. Deliberately coarse: the point
is that a coil write has a visible, physical consequence, not to model a real
clearwell.

Steady state with the golden program: raw tank cycles ~35-85% as the intake
pump duty-cycles, treated tank holds ~60-70%, header holds ~57-63 psi,
chlorine holds at the 2.5 ppm setpoint. Force any actuator and it walks off:
  * hold the intake pump on   -> raw tank climbs to 100 and overflows
  * stop the distribution pump -> header pressure bleeds to zero
  * raise the dose setpoint   -> chlorine residual chases it past 4 ppm
"""
from dataclasses import dataclass

INTAKE_RATE = 3.0        # %/s the river pump adds to the raw tank
TREATMENT_RATE = 1.2     # %/s raw -> treated while there is raw water
MUNICIPAL_DRAW = 1.2     # %/s the town consumes from the treated tank
PUMP_PSI_GAIN = 2.0      # psi/s the high-service pump adds to the header
DEMAND_PSI_BLEED = 1.1   # psi/s the municipal draw bleeds off the header


@dataclass
class WaterState:
    raw_level_pct: float = 60.0
    treated_level_pct: float = 65.0
    chlorine_ppm: float = 2.5
    header_psi: float = 60.0
    flow_gpm: float = 0.0

    def step(self, dt, *, intake_pump, dist_pump, dose_enable, dose_setpoint_ppm):
        raw_moving = self.raw_level_pct > 2.0
        to_treatment = TREATMENT_RATE if raw_moving else 0.0

        # --- raw water tank ---------------------------------------------
        inflow = INTAKE_RATE if intake_pump else 0.0
        self.raw_level_pct += (inflow - to_treatment) * dt
        self.raw_level_pct = max(0.0, min(self.raw_level_pct, 100.0))  # physical overflow

        # --- treated / clearwell --------------------------------------
        # in balance while the plant is treating; drains if the intake stops
        self.treated_level_pct += (to_treatment - MUNICIPAL_DRAW) * dt
        self.treated_level_pct = max(0.0, min(self.treated_level_pct, 100.0))

        # --- flow through the dosing point --------------------------
        self.flow_gpm = 450.0 if to_treatment else 0.0

        # --- chlorine residual --------------------------------------
        if dose_enable and self.flow_gpm > 1.0:
            # first-order approach to the PLC's setpoint, so a tampered
            # setpoint drags the residual straight up
            self.chlorine_ppm += 0.18 * (dose_setpoint_ppm - self.chlorine_ppm) * dt
        else:
            self.chlorine_ppm -= 0.03 * self.chlorine_ppm * dt
        self.chlorine_ppm = max(0.0, min(self.chlorine_ppm, 50.0))

        # --- distribution header pressure -------------------------
        self.header_psi -= DEMAND_PSI_BLEED * dt
        if dist_pump and self.treated_level_pct > 5.0:
            self.header_psi += PUMP_PSI_GAIN * dt
        self.header_psi = max(0.0, min(self.header_psi, 95.0))
        return self
