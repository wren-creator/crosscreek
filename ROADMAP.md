# Cross Creek roadmap

## v1 (in progress)

- [x] Repo scaffold, lifecycle scripts, flat + segmented compose topologies
- [x] Process core: `process-sim` + `plc-water` (OpenPLC / Modbus) + `hmi-water`
- [~] Vendor PLCs: `plc-power` (S7) + `hmi-power` done; `plc-dosing` (CIP) next
- [ ] Network boundary: `router-fw` flat ruleset, the six bridges
- [ ] Attacker box + the Session 2-4 attack scripts
- [ ] Defended half: segmented ruleset, controller hardening, `ids`, one-way historian
- [ ] `docs/architecture.md`, `docs/scenarios.md` + trainee copy, `docs/verification.md`
- [ ] *Cross Creek 101* EPUB, seven sessions
- [ ] Instructor kit: agenda, setup runbook, rubric, slide outlines, capstone CTF

## v2 and beyond

- More processes: wastewater treatment, gas pressure regulation
- More protocols: DNP3, IEC 61850 GOOSE/MMS for the substation
- Malware-analysis module: a FrostyGoop-style Go binary reimplementation run in
  a nested sandbox; students reverse the Modbus config
- Radio/serial layer: simulated licensed-band SCADA telemetry and replay attacks
- Safety Instrumented System tier plus a Triton/TRISIS-style scenario
- Blue-team dataset export (PCAP + Suricata EVE) for detection-engineering courses
- If the EPUB joins the Gumroad catalogue, add a one-paragraph series entry to
  `../books/ROADMAP.md` in the existing per-book style
