# Changelog

All notable changes to Cross Creek are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **A support-the-lab note on both HMI login pages.** `hmi/power` and
  `hmi/water` now carry a short, opt-in line beneath the sign-in form
  pointing at the developer fund (Cash App `$britleywren`). Styled to each
  panel's own palette, no popup or modal, so it stays out of the way of the
  exercises.

### Changed

- **`hmi/power` is redrawn as a browser-based SCADA control center**, modelled
  on a real utility switchyard control-room screen: a light header with a
  co-op logo mark and live clock, a Station Status card, an Alarm & Event Log
  driven off real conditions (frequency excursion, RTU CPU stop, every
  breaker command) plus a Reports view of the same log, a taller single-line
  diagram for the actual 3-breaker topology (52-F feeder, 52-T bus tie to a
  normally-open Bus B, 52-L load through transformer T1) whose line segments
  energize and de-energize off live breaker state, a Metering & Trends panel
  (rolling client-side history, frequency bars and a load line), Key Status,
  and Feeder Breaker Controls with OPEN / CLOSE / LOCKOUT per breaker
  (lockout is HMI-side only, no new RTU tag). Login page recolored to match.
- **The local generation setpoint is wired up.** `GEN_SETPOINT_MW_X10` has
  existed in the RTU's S7 DB1 since the substation vertical shipped but had
  no read, write, or UI anywhere; `hmi/power/app.py` now reports it in
  `/api/state` and accepts an `{"sp": ...}` write in `/api/cmd`, and the
  dashboard's Settings screen is a real setpoint editor for it. Diagnostics
  now shows RTU host, CPU mode, live scan count, and comms status instead of
  a stub.

### Fixed

- **The water HMI's Logon button did nothing.** The SIMATIX panel rebuild
  (0.2.0) gave the title bar a Logon / Logoff pair; Logoff went to `/logout`
  but Logon had no handler. Wired it to `/login`.

## [0.2.0] - 2026-09-03

The water plant is now a reverse-osmosis demineralisation plant with a
SIMATIX-style operator panel. The power substation and the whole defended
half are unchanged.

### Changed

- **The water plant is a two-pass RO demineralisation train** with a
  recirculating DI distribution loop, modelled on a real ultrapure-water
  plant: feed and antiscalant dosing, RO pass 1, NaOH inter-pass dosing, RO
  pass 2, a DI storage tank (3B401), a loop circulation pump (3P401), a UV
  steriliser (3UV401), and a conductivity-gated release interlock ("Release to
  Consumers"). Far more to play with: ~15 live process values, six pumps with
  per-device AUTO/HAND, four AUTO blocks, four sequences (RO / Loop / CIP /
  Sanitise), and an editable Parameters / Controllers setpoint screen.
  `process-sim/model_water.py` couples them, cut the antiscalant and the
  membranes foul, cut the NaOH and CO2 breaks through, stop the loop pump and
  the pressure bleeds out.
- **`hmi/water` is redrawn as a fictional STEMENS SIMATIX HMI "Plant
  Overview"**: the teal bezel with STEMENS / SIMATIX HMI / TOUCH and F1-F8, a
  title bar with a live clock, an alarm banner, the process mimic with a
  correct P&ID (antiscalant into the feed, NaOH inter-pass, RO2 permeate to
  the tank, the DI Loop Return closing back to the tank) and overlaid tag
  boxes, the four AUTO blocks, the sequence column, the Draw-off / Release
  indicators, and the nav tabs. Click a pump for its faceplate; Parameters and
  Controllers open a setpoint editor; Alarms lists active alarms.
- **Dropped the real "Siemens" / "SIMATIC" trademarks** for a fictional
  STEMENS SIMATIX brand. The S7 protocol keeps its universal tooling name
  (`S7comm`, `snap7`).
- **All HMI text is English.** The German panel terms are gone: "Grundbild" ->
  "Plant Overview", "Freigabe an Mischerei" -> "Release to Consumers" (coil
  `CO_FREIGABE` -> `CO_RELEASE`, `io.freigabe` -> `io.release_ok`, JSON
  `release.freigabe` -> `release.ok`), "Mischerei" -> "point of use",
  "Meldungen" -> "Alarms", "Regler" -> "Controllers", "Sanitisieren" ->
  "Sanitise", the login page, the alarm-text table, and the clock locale.
- **Water scenarios keep their shape** with RO-plant mechanisms: 4 stops the DI
  loop circulation pump (loop pressure collapse); 5 raises the release
  conductivity limit so a fouled-membrane degradation passes the quality gate;
  6 blinds the conductivity readings; 9 swaps the program to force Release
  true. Scenario 8 (`plc-dosing`) is now the NaOH inter-pass dosing
  controller; `plc-dosing` itself is unchanged, `process-sim` maps its
  `DoseRate` to the NaOH rate.
- `modbus_attack.py` subcommands are now `stop-loop`, `raise-limit`,
  `starve-antiscalant`, `restore`. `push_logic_water.py` uploads
  `crosscreek_ro_v1_PATCHED`. `recon.py creds` carries the session cookie
  through the login redirect.
- `docs/scenarios.md` (+ trainee), `docs/verification.md`,
  `docs/architecture.md`, the README, the *Cross Creek 101* Session 3 chapter
  and touches to 00/01/02/04/05/07, and the instructor slides / answer key /
  CTF are all updated to the RO plant.

## [0.1.0] - 2026-09-02

First working release. The range runs both halves end to end.

### The range

- **Scaffold and lifecycle.** `setup.sh`, `start.sh`, `stop.sh`, `status.sh`,
  `reset.sh` with the loopback-only guard in `lib.sh` and a containment probe
  in `status.sh` that confirms the attacker box cannot reach a public address.
- **Flat topology** (`docker-compose.yml`): five bridge networks along the
  Purdue model (edge, IT, DMZ, a single flat OT segment, an internal field
  bus), every published port on `127.0.0.1`, the field bus `internal`.
- **Defended topology** (`docker-compose.segmented.yml`): zones and conduits,
  every weakness toggle safe, the IDS and a DMZ jump host added. Applied by
  `./start.sh --segmented`.
- **`.env.example`**: the deliberate-weakness toggles with vulnerable defaults.

### Controllers, process, HMIs

- **`plc-water`**: a soft PLC on real Modbus/TCP :502, an OpenPLC-style 200 ms
  scan loop over a swappable `control(io)` program, and a runtime web UI on
  :8073 with a program-upload path (scenario 9, a documented vendor-download
  stand-in). `MODBUS_WRITE_OPEN` drives command validation and the keyswitch.
- **`plc-power`**: a `python-snap7` S7comm server on :102 exposing DB1 (bus
  frequency, voltage, load, breaker status/command, CPU mode). Real S7
  stop-CPU lands as a virtual-CPU STOP; `S7_NO_PASSWORD=0` re-asserts RUN and
  rejects unauthenticated breaker-open.
- **`plc-dosing`**: an embedded cpppo EtherNet/IP simulator on :44818 plus a
  Flask logic-update stand-in on :8080 that pins the metering pump wide open
  and bypasses the overdose interlock when `ENIP_ALLOW_LOGIC_DOWNLOAD=1`.
- **`process-sim`**: lumped models of the water plant and the substation bus.
  Reads actuator state over Modbus / S7 / CIP, advances the physics, writes
  sensor values back. Coarse on purpose.
- **`hmi-water`** and **`hmi-power`**: Flask + inline-SVG operator screens (a
  P&ID and a single-line diagram) that poll the PLCs and post commands.
  `DEFAULT_CREDS` gates `admin/admin`; `VERBOSE_HMI_ERRORS` leaks the tag map.
  The water HMI has per-device AUTO/HAND so manual pump commands hold against
  the running program (the safety interlocks apply in both modes); both HMIs
  toast every command and the power HMI warns when the RTU CPU is in STOP.

### Boundary, supporting hosts, IDS

- **`net/router-fw`**: Debian + nftables. Flat forwards everything and
  masquerades; segmented is default-drop with three conduits (IT↔DMZ, jump
  host→OT, historian→OT) and logs every denied cross-zone packet.
- **`attacker`**: python:slim with nmap and the open-source protocol
  libraries. No default route (blackholed); routes to the range only through
  the firewall. Scripts under `/opt/scripts` (`recon`, `modbus_attack`,
  `s7_attack`, `cip_attack`, `push_logic_water`) cover scenarios 1-9,
  hardcoded to lab addresses.
- **`eng-ws`**: serves the PLC project files and a `notes.txt` with every
  controller credential, plus an unauthenticated remote-desktop port when
  `EXPOSE_REMOTE_ACCESS=1`.
- **`historian`**: polls the water PLC and the RTU into sqlite;
  `HISTORIAN_READONLY` gates the write-back path.
- **`net/ids`**: Suricata 8 (community image; the package was dropped from
  Debian 12) sharing the firewall's namespace. Six rules; a `:9411` text tail.

### Documentation and course

- **`docs/scenarios.md`** and **`-trainee.md`**: all ten planted weaknesses in
  the fixed shape, each with the real incident, the exact command, the
  physical consequence observed against the running range, and a fix mapped to
  a CISA CPG and an ISA/IEC 62443 clause. Framework-mapping table.
- **`docs/verification.md`**: Sections A-E, one row per scenario for the attack
  side and the defended re-run.
- **`docs/architecture.md`**: segment map, the flat-vs-segmented firewall, the
  IDS placement, and the three mechanics worth spelling out.
- **`docs/Cross-Creek-101-Syllabus.epub`**: a seven-session course (source
  under `docs/syllabus-epub/`), same structure as the Mainframe 100 series.
- **`instructor/`**: a timed agenda, a setup runbook, a grading rubric, an
  answer key, seven slide decks, and an eight-flag capstone CTF with
  `check-flags.sh`.

### Verified

- Flat: from the contained attacker box, `recon` maps all five OT devices,
  `admin/admin` opens both HMIs, `notes.txt` yields the credentials, and the
  Modbus / S7 / CIP / logic-push attacks all land with visible HMI effects
  (chlorine past 15 ppm, header pressure collapsing, feeder breaker open,
  frequency past 53 Hz, raw tank overflowing).
- Segmented: the same attacks time out at the firewall (CC-FW-DROP counter
  climbing), `recon` finds nothing, and each attempt raises a Suricata alert
  at `http://127.0.0.1:9411/`.
- `./status.sh` reports loopback-only and no attacker egress. The EPUB builds
  clean. The CTF checker scores 8/8 against the live range.

## Project status

Cross Creek is a training range, not a product. The scenario set, container
layout, and default ports may change between revisions. Reset the range
between cohorts, several scenarios are stateful.
