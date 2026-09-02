# Changelog

All notable changes to Cross Creek are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- IDS (`net/ids/`): Suricata 8 (community image; the package was dropped from
  Debian 12) sharing the firewall's network namespace, so it sees every
  segment. Six Cross Creek rules flag edge hosts reaching a PLC port, ICS
  protocols spoken by a non-HMI source, and the two program-download paths. A
  `:9411` text endpoint tails the alerts. Verified in segmented mode: the
  attacker's Modbus/S7/CIP attempts time out at the firewall (240+ packets on
  the CC-FW-DROP counter) and each attempt raises an alert.

### Added
- Network boundary and the attacker workstation: the flat range is now
  attackable end to end from a contained box.
  - `net/router-fw/`: a Debian + nftables container bridging edge, IT, DMZ and
    OT. `FLAT` forwards everything and masquerades so the attacker's replies
    return; `SEGMENTED` is default-drop with only the IT<->DMZ, jump-host->OT
    and historian->OT conduits open, every denied cross-zone packet logged.
  - `attacker/`: python:slim + nmap and the open-source protocol libraries.
    Its entrypoint routes to the range only through the firewall and
    blackholes any default route. Scripts (`recon`, `modbus_attack`,
    `s7_attack`, `cip_attack`, `push_logic_water`) are hardcoded to lab
    addresses and cover scenarios 1-9.
  - `eng-ws/`: serves the PLC project files and a `notes.txt` with every
    controller address and password, plus an unauthenticated remote-desktop
    port when `EXPOSE_REMOTE_ACCESS=1`.
  - `historian/`: polls the water PLC (Modbus) and RTU (S7) into sqlite;
    `HISTORIAN_READONLY` gates the write-back path.
  - The OT network is now a single flat segment (as small utilities really
    are); the Session 5 lesson is segmenting it. `edge-net` is no longer
    `internal` (that blocked routing through the firewall); containment is a
    no-egress attacker plus a `status.sh` reachability probe.
  - Verified: from the attacker box, `recon.py sweep` maps all five OT
    devices, `admin/admin` opens both HMIs, `notes.txt` yields the
    credentials, and the Modbus/S7/CIP/logic attacks all land with visible
    effects on the HMIs. `./status.sh` confirms the box has no internet.

### Added
- Dosing controller: `plc-dosing`, wired into `process-sim` over CIP.
  - `plc/dosing-enip/`: an embedded cpppo EtherNet/IP simulator on :44818
    carrying `DoseSetpoint`, `DoseRate`, `FlowFeedback`, `Mode`, `LogicRev`,
    `LogicForced`. A Flask service on :8080 is the unauthenticated
    logic-update stand-in; POST while `ENIP_ALLOW_LOGIC_DOWNLOAD=1` forces the
    metering pump to 100% and bypasses the downstream overdose interlock.
  - `process-sim` gains a CIP loop: reads `DoseRate`/`LogicForced`, writes
    `FlowFeedback`, and feeds an effective dose target into the water model.
    `model_water.step()` now takes `dosing_active` + `dose_target_ppm` so
    Modbus setpoint tamper, CIP rate tamper, and a CIP logic push all read as
    chlorine.
  - Verified: a CIP write to `DoseSetpoint` drives the residual into the
    interlock; a logic push runs it to ~20 ppm with the interlock powerless.

### Added
- Substation vertical: `plc-power` + `hmi-power`, wired into `process-sim`.
  - `plc/power-s7/`: a python-snap7 server on :102 exposing DB1 (bus frequency,
    voltage, load, breaker status/command, CPU mode). Real S7 stop-CPU lands as
    a virtual-CPU STOP; `S7_NO_PASSWORD=0` makes the scan loop force RUN back
    and ignore unauthenticated breaker-open commands.
  - `process-sim/model_power.py`: grid-tied vs islanded bus model. Open the
    feeder breaker and the bus islands; the generation/load imbalance then
    ramps the frequency past the excursion alarm.
  - `hmi/power/`: single-line-diagram HMI, breaker close/trip controls writing
    the S7 command byte.
  - Verified: `plc_stop()` over S7comm stops the RTU; a DB write to the command
    byte trips the load breaker (voltage rises, load sheds); islanding drives a
    watchable over-frequency excursion.
  - snap7's C client needs an IP, so `process-sim` and `hmi-power` resolve the
    PLC hostname before connecting.

### Added
- Process core: the water plant runs end to end.
  - `plc/water-openplc/`: a soft PLC serving real Modbus/TCP on :502, an
    OpenPLC-style 200 ms scan loop over a swappable `control(io)` program, and
    a runtime web UI on :8073 (view program, stop/start CPU, upload program).
    The upload path is scenario 9 and is a documented stand-in for a vendor
    download. `MODBUS_WRITE_OPEN` toggles command validation and the keyswitch.
  - `process-sim/`: a lumped physical model (raw tank, clearwell, chlorine
    residual, header pressure) that reads the PLC's actuator coils over Modbus
    and writes sensor values back every tick.
  - `hmi/water/`: Flask + inline-SVG P&ID; browser polls `/api/state`, controls
    POST to `/api/cmd`. `DEFAULT_CREDS` gates `admin/admin`; `VERBOSE_HMI_ERRORS`
    leaks tracebacks and the tag map.
  - Verified against the running stack: a Modbus register write drives chlorine
    past the overdose threshold; a logic upload with the interlock removed holds
    the intake pump on and overflows the raw tank.
- Host HMI/UI ports moved off 8081-8091 (collision with a local service) to
  8071 (water HMI), 8072 (power HMI), 8073 (water PLC runtime UI).

### Added (scaffold)
- Repo scaffold: lifecycle scripts (`setup.sh`, `start.sh`, `stop.sh`,
  `status.sh`, `reset.sh`) with the loopback-only guard in `lib.sh` and an
  attacker-containment check in `status.sh`.
- `docker-compose.yml` flat topology: six network segments mapped to the Purdue
  model (edge, enterprise, DMZ, OT-HMI, OT-PLC, field), all host ports bound to
  `127.0.0.1`, edge and field networks `internal`.
- `docker-compose.segmented.yml` override for the defended topology: zones and
  conduits, weakness toggles off, IDS on, one-way historian, DMZ jump host.
- `.env.example` weakness toggles with vulnerable defaults.
- Documentation stubs: `docs/architecture.md`, `docs/scenarios.md`,
  `docs/scenarios-trainee.md`, `docs/verification.md`.
- `ROADMAP.md`.

### Not yet built
- Service images (`plc/*`, `process-sim/`, `hmi/*`, `eng-ws/`, `historian/`,
  `net/router-fw/`, `net/ids/`, `attacker/`) land in follow-up commits, one
  vertical slice at a time per the build order in the plan.
- *Cross Creek 101* EPUB and the instructor kit.

## Project status

Cross Creek is a training range, not a product. The scenario set, container
layout, and default ports may change between revisions. Reset the range between
cohorts, several scenarios are stateful.
