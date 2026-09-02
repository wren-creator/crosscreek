# Changelog

All notable changes to Cross Creek are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
