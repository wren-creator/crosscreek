# Session 4 — Vendor Dialects (S7comm, EtherNet/IP)

## Slide 1: S7comm and the RTU (scenario 7)
- the S7 controller family family, TCP 102. Carries stop/start/mode alongside data.
- Often no password. Industroyer operated Kyiv breakers with protocol-native commands (2016).
- `s7_attack.py trip feeder` → island the bus; `trip load` → frequency ramps past 50.5 Hz
- `s7_attack.py stop` → RTU frozen, operator keeps the screen, loses control

## Slide 2: EtherNet/IP + CIP (scenario 8)
- Allen-Bradley, TCP 44818. Tag read/write unauthenticated. Keyswitch REMOTE = downloads allowed.
- `cip_attack.py set 15` → NaOH overdose → RO2 conductivity past the limit → **interlock still holds Release**
- `cip_attack.py logic-push` → LogicForced, NaOH pump pinned 100%, loop conductivity climbs; release still needs scenario 5 or 9

## Slide 3: Honest scope note
- Real Studio 5000 download can't be emulated without Rockwell tooling
- The range runs an unauthenticated service that swaps the logic and bumps `LogicRev`
- Real: the concept + the detection. Stand-in: the wire format.

## Slide 4: Remove the release interlock (scenario 9)
- OpenPLC-style runtime, `:8073`, login `openplc/openplc` (from `notes.txt`)
- `push_logic_water.py` uploads golden-minus-the-release-interlock (Release forced true) and minus the RO2 hard-safety
- On its own: latent — the safety is gone but nothing bad yet

## Slide 5: Chain 3.5 + 8b + 9
- Membranes fouled + caustic pinned + quality gate raised + interlock deleted → off-spec DI water to the point of use
- This is the on-the-news outcome

## Slide 6: What you should notice
- Vendor protocols gave you *more*, not more difficulty
- The danger in every scenario was the second step — the one that removed the safety
- An intruder who only tampers with values gets caught by a good program. One who changes the program does not.
