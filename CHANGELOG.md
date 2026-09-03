# Changelog

All notable changes to Cross Creek are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
