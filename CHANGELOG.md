# Changelog

All notable changes to Cross Creek are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
