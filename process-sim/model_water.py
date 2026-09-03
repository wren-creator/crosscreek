"""Lumped model of the Cross Creek RO demineralisation plant.

Fourteen numbers. Each step takes the actuator states the PLC set and advances
the physical values by `dt` seconds. Coarse on purpose: the point is that a
coil or register write has a visible, physical consequence, not to model
membrane transport.

Steady state, all AUTO, nominal reagents:
  feed ~8 m3/h at ~4.5 bar, RO1 permeate ~12 uS/cm, NaOH inter-pass dosing
  brings RO2 permeate to ~0.5 uS/cm, the DI tank cycles 40-85% as the RO
  sequence duty-cycles, the loop holds ~3.8 bar, UV ~95%, loop return
  ~0.7 uS/cm. The release interlock is satisfied.

Force something and it walks off:
  * stop the loop pump (3P401)        -> loop pressure bleeds to zero
  * starve the antiscalant            -> membranes foul, RO1 then RO2 conductivity climb
  * cut the NaOH inter-pass dose      -> RO2 conductivity climbs (CO2 breakthrough)
  * raise the release conductivity limit, or swap the logic -> off-spec water is released
"""
from dataclasses import dataclass


def _clamp(x, lo, hi):
    return max(lo, min(x, hi))


@dataclass
class RoWaterState:
    feed_flow_m3h: float = 8.0
    feed_press_bar: float = 4.5
    ro1_cond_us: float = 12.0
    ro2_cond_us: float = 0.55
    ro2_press_bar: float = 12.0
    ro_recovery_pct: float = 75.0
    di_tank_pct: float = 70.0
    loop_press_bar: float = 3.8
    loop_flow_m3h: float = 3.5
    loop_ret_cond_us: float = 0.75
    antiscalant_tank_pct: float = 80.0
    naoh_tank_pct: float = 80.0
    uv_intensity_pct: float = 95.0
    fouling: float = 0.0            # 0..1, drives RO1 conductivity up

    def step(self, dt, *, p102_feed, p101_antiscalant, p301_ro1, p302_ro2,
             p401_loop, uv401, seq_cip, abnahme, loop_press_sp,
             antiscalant_rate_lh, naoh_rate_lh, contaminant_us=0.0):
        feeding = p102_feed and not seq_cip

        # --- feed / pretreatment ------------------------------------------
        self.feed_flow_m3h += ((8.0 if feeding else 0.0) - self.feed_flow_m3h) * min(1.0, 2.0 * dt)
        self.feed_press_bar += ((4.5 if p102_feed else 0.0) - self.feed_press_bar) * min(1.0, 2.0 * dt)
        if p101_antiscalant:
            self.antiscalant_tank_pct -= antiscalant_rate_lh * 0.02 * dt
        if p302_ro2:
            self.naoh_tank_pct -= naoh_rate_lh * 0.02 * dt
        self.antiscalant_tank_pct = _clamp(self.antiscalant_tank_pct, 0.0, 100.0)
        self.naoh_tank_pct = _clamp(self.naoh_tank_pct, 0.0, 100.0)

        # --- membrane fouling: adequate antiscalant keeps it near zero ----
        adequate = (p101_antiscalant and antiscalant_rate_lh >= 1.5
                    and self.antiscalant_tank_pct > 5.0)
        if feeding:
            self.fouling += (-0.02 if adequate else 0.03) * dt
        self.fouling = _clamp(self.fouling, 0.0, 1.0)

        # --- RO pass 1 ---------------------------------------------------
        if p301_ro1 and feeding:
            base1 = 12.0 + 40.0 * self.fouling
            self.ro1_cond_us += (base1 - self.ro1_cond_us) * min(1.0, 0.4 * dt)
        # else: holds

        # --- RO pass 2 (NaOH-assisted polish) --------------------------
        if p302_ro2 and p301_ro1:
            naoh_factor = _clamp(1.0 - (naoh_rate_lh - 1.0) / 6.0, 0.2, 2.5)
            base2 = (0.6 + 0.02 * self.ro1_cond_us) * naoh_factor
            if self.ro1_cond_us > 50.0:
                base2 += (self.ro1_cond_us - 50.0) * 0.1
            if naoh_rate_lh > 6.0:                 # caustic overdose adds ions too
                base2 += (naoh_rate_lh - 6.0) * 0.8
            self.ro2_cond_us += (base2 - self.ro2_cond_us) * min(1.0, 0.4 * dt)
        else:
            self.ro2_cond_us += (max(self.ro1_cond_us * 0.3, 0.2) - self.ro2_cond_us) * min(1.0, 0.05 * dt)
        self.ro2_press_bar += ((12.0 if p302_ro2 else 0.0) - self.ro2_press_bar) * min(1.0, 2.0 * dt)

        # --- recovery -------------------------------------------------
        if self.feed_flow_m3h > 0.5:
            self.ro_recovery_pct += ((75.0 - 30.0 * self.fouling) - self.ro_recovery_pct) * min(1.0, dt)

        # --- DI storage tank ----------------------------------------
        fill = 3.0 if p302_ro2 else 0.0
        draw = 2.2 if abnahme else 0.8
        self.di_tank_pct = _clamp(self.di_tank_pct + (fill - draw) * dt, 0.0, 100.0)

        # --- distribution loop -------------------------------------
        if p401_loop and self.di_tank_pct > 5.0:
            self.loop_press_bar += 2.0 * (loop_press_sp - self.loop_press_bar) * dt
        else:
            self.loop_press_bar -= 1.5 * dt
        self.loop_press_bar = _clamp(self.loop_press_bar, 0.0, 8.0)
        self.loop_flow_m3h += (((3.5 + (1.5 if abnahme else 0.0)) if p401_loop else 0.0)
                               - self.loop_flow_m3h) * min(1.0, 2.0 * dt)

        # --- UV steriliser ----------------------------------------
        if uv401:
            self.uv_intensity_pct += (95.0 - self.uv_intensity_pct) * min(1.0, 1.5 * dt)
        else:
            self.uv_intensity_pct = _clamp(self.uv_intensity_pct - 20.0 * dt, 0.0, 100.0)

        # --- loop return conductivity ---------------------------
        target = (max(self.ro2_cond_us * 1.2, 0.1)
                  + (3.0 if self.uv_intensity_pct < 70.0 else 0.0)
                  + contaminant_us)
        self.loop_ret_cond_us += (target - self.loop_ret_cond_us) * min(1.0, 0.06 * dt)
        self.ro1_cond_us = _clamp(self.ro1_cond_us, 0.1, 200.0)
        self.ro2_cond_us = _clamp(self.ro2_cond_us, 0.02, 100.0)
        self.loop_ret_cond_us = _clamp(self.loop_ret_cond_us, 0.02, 100.0)
        return self
