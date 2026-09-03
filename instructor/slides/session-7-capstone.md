# Session 7 — Capstone and Incident Response

## Slide 1: One foothold
- Assume: shell on the engineering workstation. Earn everything else.
- Time-box the flat chain to 45 minutes.

## Slide 2: The chain (flat range)
1. `recon.py engws` — notes.txt, addresses, runtime login, golden program
2. `recon.py sweep` + `creds` — confirm layout, log into both HMIs
3. `modbus_attack.py raise-limit 5.0` + `starve-antiscalant` — quality gate defeated, membranes foul
4. blind the water HMI — hold IR mirror at nominal
5. `push_logic_water.py` — force Freigabe true, drop the RO2 hard-safety
6. `cip_attack.py logic-push` — NaOH pump pinned 100%, loop conductivity climbs
7. `s7_attack.py trip feeder` + `trip load` — island + frequency excursion
8. `s7_attack.py stop` — freeze the RTU
- End state: RO plant releasing off-spec DI water, HMI shows green, substation dark

## Slide 3: The write-up
- Narrative / Evidence / Impact / Remediation
- Plant manager AND regulator can both read it
- Per step: the control that breaks it + CPG + 62443 + effort estimate
- Hand out `rubric.md`

## Slide 4: Break the chain (`./start.sh --segmented`)
| Step | Dies at |
|---|---|
| 1–2 | share + factory accounts gone; jump host only |
| 3 | firewall drop / PLC allowlist; IDS alert |
| 4 | HMI plausibility check |
| 5 | keyswitch RUN, upload refused |
| 6 | controller out of REMOTE, 403 |
| 7–8 | RTU auth, re-asserts RUN; IDS alert |

## Slide 5: IR tabletop (45 min, no keyboards)
- 02:00, low-pressure alarm, HMI looks normal
- Detect / Contain / Eradicate / Recover / Report
- Reference: CISA + EPA water-sector IR guidance
- Goal: find the "we would just..." sentence that doesn't survive 02:00

## Slide 6: Closing the loop
- Attacked with a Python client and a browser; closed every hole with planning
- The utilities in the news were unsegmented, had default passwords, never ran the tabletop
- Now you have
