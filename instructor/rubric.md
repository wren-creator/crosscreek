# Cross Creek 101 — capstone grading rubric

The deliverable is the Session 7 write-up: the flat-range attack chain, then
proof that the segmented range breaks every link. Score out of 100.

## Attack chain executed (30)

| Points | Criteria |
|---|---|
| 30 | All nine steps run (DNS recon through the two-step release), each with the observed HMI/historian reading before and after, and the physical meaning stated |
| 20 | Seven or eight steps, effects observed |
| 10 | Attacks run but effects not tied to a physical consequence |
| 0 | Not attempted, or run against something other than the range |

## Write-up quality (30)

| Points | Criteria |
|---|---|
| 30 | Narrative / Evidence / Impact / Remediation all present; a plant manager and a regulator could both read it; exact commands included |
| 20 | All four sections present, some hand-waving in Impact or Remediation |
| 10 | Missing a section, or reads as a command log rather than a report |
| 0 | Not submitted |

## Remediation mapping (25)

| Points | Criteria |
|---|---|
| 25 | Every step mapped to a specific control from Sessions 5–6, each with its CISA CPG and its ISA/IEC 62443 clause, plus a realistic effort estimate |
| 15 | Controls named for every step, framework references thin or partial |
| 8 | Generic advice ("segment the network") not tied to the specific step |
| 0 | Absent |

## Segmented-range proof (15)

| Points | Criteria |
|---|---|
| 15 | Re-ran the chain in `--segmented`, recorded exactly where each step dies and why (firewall drop / allowlist / keyswitch / auth / plausibility check), included an IDS alert as evidence |
| 8 | Showed the chain fails but not the mechanism for each step |
| 0 | Not attempted |

## Automatic deductions

- −20: any command in the write-up was pointed at an address that is not a
  Cross Creek lab address
- −10: the ethics/authorised-use section of the report is missing
- −5 each: a claimed effect that the range does not actually produce (check
  against `docs/scenarios.md`)

## Notes for the grader

The strongest reports treat the interlock behaviour honestly: scenarios 5 and
8a are *contained* by the PLC logic on their own, and the report should say so
and explain that the danger is the second step (9 / 8b) that removes the
safety. A report that claims the bare setpoint write poisoned the water supply
has not understood what it saw.
