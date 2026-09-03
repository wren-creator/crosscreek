# Session 3 — Speaking the Machines' Language (Modbus)

## Slide 1: The plant
- Two-pass RO demineralisation plant → DI storage tank → recirculating distribution loop → UV → the "point of use"
- Release interlock ("Release to Consumers"): only release when RO2 + loop conductivity < limit, UV ok, tank not empty
- That interlock is what you attack

## Slide 2: What Modbus is
- 1979. Request/response over TCP 502. Coils (bits) and registers (16-bit words).
- No auth, no session, no signing. Open port 502 = you are the HMI.
- FrostyGoop's Modbus part was function code 6. The same call the HMI makes every second.

## Slide 3: Enumerate
- `modbus_attack.py enum` — coils, discretes, holding, input registers
- Coil 4 = 3P401 loop pump, coil 6 = CPU keyswitch, HR0 = loop pressure SP, HR5 = release conductivity limit
- Full map in `plc/water-openplc/mapfile.py`; deriving the interesting registers from the panel is the exercise

## Slide 4: Stop the distribution loop (scenario 4)
- Bare coil write to stop 3P401 fails: the program re-asserts it in 200 ms
- Lesson: take the pump to HAND first (program stops driving it), then stop it
- `modbus_attack.py stop-loop` → 3PITC401 bleeds from 3.8 bar to 0 in seconds → `DI_LOOP_PRESS_LOW`

## Slide 5: Defeat the quality gate (scenario 5)
- The dangerous attack is releasing unsafe water, not stopping a pump
- `modbus_attack.py raise-limit 5.0` → HR5 = 500 (design limit is 2.0) — harmless on its own
- `modbus_attack.py starve-antiscalant` → membranes foul → 1QAH301 12→50 µS/cm, 2QAH401 follows past 2
- With the limit raised, `DI_COND_HIGH_RO2` never trips, Release stays green → off-spec water released
- **Shape:** setpoint write alone = harmless; membrane foul alone = caught; both together = through. The interlock's hard limit (a program constant) is the last line — Session 4.

## Slide 6: Blind the operator (scenario 6)
- HMI reads IR 0–14; sim writes the field block; PLC mirrors it
- Write the mirror (IR 3 = RO2 cond, IR 6–9) faster than the sim → operator sees spec + green
- Stuxnet's operator-facing trick, in miniature

## Slide 7: What you should notice
- No credential, no exploit — and the only safety was an interlock an engineer coded, with a register you could turn off
- Session 5 can't fix Modbus. It fixes who can reach 502, which setpoints the program accepts, and whether the release limit is writable at all.
