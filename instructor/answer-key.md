# Cross Creek 101 — instructor answer key

The full per-scenario answer key is `docs/scenarios.md` (the instructor
edition). This file is the teaching notes around it.

## The one thing students get wrong

Scenarios 5 and 8a (setpoint / tag tamper) are **contained by the golden PLC
logic**. The overdose interlock cuts the metering pump near 4 ppm. Students
watch chlorine climb, see it stop, and either think they failed or think they
succeeded at poisoning the water. Neither. The lesson is that a *well-written
control program is itself a control*, and the dangerous attack is the one that
removes it: scenario 9 (replace the water PLC program) or 8b (CIP logic push).
Drive this point home in the Session 4 debrief.

## Session-by-session emphasis

| Session | The point to land |
|---|---|
| 1 | The range is contained and you proved it. OT is a network that was never meant to have a hostile host, and it shows. |
| 2 | The 2021–2024 water intrusions were exposure + default creds + an open share. No exploits. |
| 3 | Modbus has no security model. A read and a write are the same risk. Running PLC logic fights a coil write, so attack the register it reads. |
| 4 | Vendor protocols give you *more*: stop a CPU, operate a breaker, rewrite the logic. The dangerous step is always the one that removes a safety. |
| 5 | You broke every attack without patching a protocol. You changed who can talk to what and made the controllers stop trusting the network. |
| 6 | Seven controls, none exotic. The plants in the news had done none of them. |
| 7 | The gap between how little the attack needed and how ordinary the defense was — that is the whole course. |

## Framework references students should be able to cite by the end

- **MITRE ATT&CK for ICS**: the technique IDs in `scenarios.md` (T0812, T0836,
  T0843, T0855, T0856, T0858, T0883, T0889 are the load-bearing ones)
- **CISA Cross-Sector CPGs**: 1.E (change management), 2.A (default passwords),
  2.F (no exploitable internet-exposed services), 2.H (MFA), 3.A (detection),
  5.A (segmentation), 7.A (backups)
- **ISA/IEC 62443**: zones and conduits, security levels SL-1/SL-2, defensive
  coding in the control program
- **CISA / EPA / AWWA "Top Cyber Actions for Securing Water Systems"**: the
  segmented topology turns on every item on that list

## If you have extra time

- Have students diff the golden and attacker programs in `push_logic_water.py`
  and identify the exact removed lines.
- Wireshark on the attacker's Modbus traffic: show them function code 6 on the
  wire and that it is identical to the HMI's traffic.
- Let a fast group try to write their own HMI-blinding loop from scratch
  rather than using the sketch in Session 3.
