"""Golden control program for the Cross Creek RO demineralisation plant.

OpenPLC-style: one `control(io)` function, called every scan. `io` is a live
view of the process; set the outputs and return.

Sequences and equipment can run in AUTO or HAND. In AUTO the program below
drives them. In HAND the operator drives them from the HMI and the program
leaves that output alone, except for the safety interlocks, which apply in
both modes.

This is the known-good logic. `./reset.sh` reloads it. Scenario 9 replaces the
running copy with an attacker version that strips the release interlock.
"""

PROGRAM_NAME = "crosscreek_ro_v1 (golden)"


def control(io):
    cip = io.seq_cip or io.seq_sanitise

    # --- RO makeup: run the RO sequence on DI tank level -------------------
    if not io.ro_valves_hand:
        if io.di_tank_pct <= io.tank_lo_sp:
            io.seq_ro = True
        elif io.di_tank_pct >= io.tank_hi_sp:
            io.seq_ro = False
        if cip:                       # never make product during a clean
            io.seq_ro = False

    # --- feed / pretreatment -------------------------------------------
    if not io.p102_hand:
        io.p102_feed = io.seq_ro and not cip
    if not io.p101_hand:
        # antiscalant doses whenever feed water is flowing and there is reagent
        io.p101_antiscalant = io.p102_feed and io.antiscalant_tank_pct > 2.0

    # --- RO passes ---------------------------------------------------
    if not io.p301_hand:
        io.p301_ro1 = io.p102_feed and io.feed_press_bar > 1.0
    if not io.p302_hand:
        io.p302_ro2 = io.p301_ro1 and io.ro1_cond_us < 50.0

    # Hard safety: do not push grossly off-spec permeate toward the tank.
    if io.ro2_cond_us > io.cond_hard_limit and not io.bypass_release_ilk:
        io.p302_ro2 = False

    # --- DI loop ---------------------------------------------------
    if not io.loop_valves_hand:
        io.seq_loop = True            # the loop circulates continuously
    if not io.p401_hand:
        io.p401_loop = io.seq_loop
    if not io.uv_hand:
        io.uv401 = io.seq_loop        # UV runs with the loop

    # --- release interlock: "Release to Consumers" -----------------
    quality_ok = (
        io.ro2_cond_us <= io.cond_limit_us
        and io.loop_ret_cond_us <= io.cond_limit_us
        and io.uv_intensity_pct >= io.uv_min_intensity
        and io.di_tank_pct > 10.0
    )
    io.release_ok = quality_ok or io.bypass_release_ilk
