# Cross Creek 101 — instructor agenda

Two days, roughly six contact hours each. Works as 4 half-days for a part-time
cohort. Every block is: short brief, hands-on, debrief. Keep the lecture under
a third of each block.

## Day 1 — the attack half

| Time | Block | Notes |
|---|---|---|
| 0:00 | Welcome, the two headlines (Aliquippa, FrostyGoop), the ethics line | Session 1 §1.1. Do not skip. Get verbal buy-in on the authorised-use rule. |
| 0:20 | Bring the range up, run `status.sh`, prove containment | Everyone gets `./setup.sh && ./start.sh` green before moving on. Have the offline-image fallback ready (setup runbook). |
| 0:45 | Session 1: the Purdue model, map the plant by hand | Students produce a written attack-surface map. Collect it. |
| 1:30 | Break | |
| 1:45 | Session 2: exposure and access (scenarios 1–3) | Everyone logs into an HMI with `admin/admin` and reads `notes.txt`. |
| 2:45 | Lunch | |
| 3:30 | Session 3: Modbus (scenarios 4–6) | Pair them. One drives the attack, one watches the HMI. Swap. |
| 4:45 | Break | |
| 5:00 | Session 4: vendor dialects (scenarios 7–9) | The logic-push is the "aha". Make sure everyone sees chlorine pass 4 ppm. |
| 5:45 | Day 1 debrief: what did any of that actually require? | Answer should be "nothing". Set up Day 2. |

## Day 2 — the defense half

| Time | Block | Notes |
|---|---|---|
| 0:00 | Recap, then `./start.sh --segmented` | |
| 0:20 | Session 5: segmentation, allowlisting, hardening (D1–D3) | Students re-run a Day 1 attack after each control and record where it dies. |
| 1:45 | Break | |
| 2:00 | Session 6: monitoring, integrity, remote access, recovery (D4–D7) | Everyone watches an alert land at `:9411`. Everyone runs `./reset.sh`. |
| 3:15 | Lunch | |
| 4:00 | Session 7: the capstone chain, flat then segmented | Time-box the flat chain to 45 min. Then the segmented walk-through. |
| 5:00 | The write-up (start it here, finish as homework) | Hand out `rubric.md`. |
| 5:30 | Incident-response tabletop | Session 7 §7.4. No keyboards. |
| 6:00 | Close, the CTF as optional homework | `instructor/ctf/` |

## Materials checklist

- One machine per student (or per pair) with Docker, 8 GB RAM free, the repo cloned
- The offline image bundle (see `setup-runbook.md`) on a USB drive as backup
- Printed copies of `scenarios-trainee.md` and `rubric.md`
- Instructor holds `scenarios.md` and `ctf/answers.txt`
