# Cross Creek

A mock municipal water treatment plant and power substation, with simulated
PLCs, for authorised ICS and OT security training. It ships wired with the
weaknesses that are actually getting utilities compromised right now, a
step-by-step attack curriculum modeled on real incidents, and a defended
topology you switch on to close every one of them.

> Use Cross Creek only: on your own machine; in a lab you control; in a
> classroom or range where you have permission; under written rules of
> engagement for authorised training or assessment. Never point a Cross Creek
> command, script, payload, scan, or credential at a real utility, a real PLC,
> or any system you do not own. ICS attacks have physical consequences. People
> can be hurt. This range exists so you never have to learn that on a live one.

## Overview

One `docker-compose.yml` stands up a small municipal utility: a three-stage
water plant (raw intake, chlorine dosing, distribution pressure) and a
single-bus power substation, driven by three simulated controllers that speak
real protocols, Modbus/TCP, EtherNet/IP (CIP), and Siemens S7comm. A Python
process simulator plays the part of the physical world: open a valve and the
chlorine rises, stop a pump and the tower drains. Two web HMIs show operators a
P&ID and a single-line diagram. A firewall container sits on the boundary
between the enterprise, DMZ, and OT segments. An attacker workstation sits on a
hostile "edge" network with no route off the lab.

The default (flat) topology is the *how the attacks work* half: the boundary
forwards freely and every weakness is on. Run `./start.sh --segmented` for the
*now secure it* half: zones and conduits enforced, protocol allowlists,
controller hardening, an ICS-aware IDS, a one-way historian, and a DMZ jump
host. The same attacks, re-run against the segmented range, fail, and the IDS
shows you why.

Every host port binds to `127.0.0.1`. The edge and field networks are marked
`internal`, so nothing on them can reach the internet. `start.sh` refuses to
launch if any port would bind beyond loopback; `status.sh` re-audits and checks
the attacker box has no default route.

## Quick start

```bash
# one-time: preflight checks, build the images
./setup.sh

# bring the range up with vulnerable defaults (the attack half)
#   water HMI       http://127.0.0.1:8071/
#   power HMI       http://127.0.0.1:8072/
#   water PLC       127.0.0.1:5020   Modbus/TCP
#   dosing PLC      127.0.0.1:4840   EtherNet/IP (CIP)
#   substation RTU  127.0.0.1:1020   S7comm
./start.sh

# health, loopback bind audit, attacker-containment check
./status.sh

# drop into the attacker workstation
docker exec -it crosscreek-attacker bash

# bring it up defended instead, and re-run the attacks
./start.sh --segmented

# restore golden state between cohorts (also the Session 6 recovery drill)
./reset.sh

# stop, keep data / stop and wipe volumes
./stop.sh
./stop.sh --all
```

## Layout

| Path | Description |
|---|---|
| `docker-compose.yml` | the range, flat topology: six segments, `127.0.0.1` bindings, weaknesses on |
| `docker-compose.segmented.yml` | override that applies the defended topology |
| `plc/water-openplc/` | OpenPLC runtime, water intake + distribution logic, Modbus/TCP |
| `plc/dosing-enip/` | Allen-Bradley-style dosing controller, EtherNet/IP (CIP) |
| `plc/power-s7/` | Siemens-style substation RTU, S7comm |
| `process-sim/` | the physics: tank levels, chlorine ppm, bus frequency, breaker state |
| `hmi/water/` `hmi/power/` | the two operator screens (Flask + SVG) |
| `eng-ws/` | engineering workstation, holds PLC project files and creds: the pivot box |
| `historian/` | data historian in the DMZ, one-way replication in segmented mode |
| `net/router-fw/` | the boundary firewall, `flat` and `segmented` nftables rulesets |
| `net/ids/` | Suricata + Zeek with ICS rules (segmented mode) |
| `attacker/` | analyst workstation: nmap, pymodbus, pycomm3, python-snap7, tshark, scripts |
| `docs/scenarios.md` | instructor answer key: every planted weakness, exploit, physical effect, fix |
| `docs/scenarios-trainee.md` | trainee copy with the fix removed |
| `docs/architecture.md` | segments, addresses, volumes, toggles, and the tricky mechanics |
| `docs/verification.md` | end-to-end test runbook, attack side and defended side |
| `docs/syllabus-epub/` | source for *Cross Creek 101*, a seven-session syllabus |
| `docs/Cross-Creek-101-Syllabus.epub` | the built syllabus ebook (`docs/syllabus-epub/build-epub.sh`) |
| `instructor/` | timed agenda, setup runbook, grading rubric, slide outlines, capstone CTF |
| `setup.sh` `start.sh` `stop.sh` `status.sh` `reset.sh` | lifecycle scripts |

## Services and ports

| Service | Host bind | Purpose |
|---|---|---|
| water HMI | `127.0.0.1:8071` | water plant operator screen |
| power HMI | `127.0.0.1:8072` | substation operator screen |
| water PLC (OpenPLC UI) | `127.0.0.1:8073` | runtime web UI, used for the logic-download exercise |
| water PLC (Modbus) | `127.0.0.1:5020` | Modbus/TCP, container port 502 |
| dosing PLC (CIP) | `127.0.0.1:4840` | EtherNet/IP, container port 44818 |
| substation RTU (S7) | `127.0.0.1:1020` | S7comm, container port 102 |
| IDS events | `127.0.0.1:9411` | Suricata EVE tail, segmented mode only |
| process-sim, historian, router-fw, eng-ws | not published | internal only |

## Scenarios

Ten planted weaknesses in four groups, each tied to a published incident and
mapped to MITRE ATT&CK for ICS:

- **Exposure and access** (3): internet-exposed HMI with default credentials
  (Aliquippa, 2023), an unauthenticated remote-access service to the OT LAN
  (Oldsmar, 2021), and an engineering workstation reachable from the enterprise
  net that holds project files and PLC credentials.
- **Protocol abuse** (3): unauthenticated Modbus coil writes that stop the
  distribution pump (FrostyGoop, Lviv, 2024), holding-register setpoint
  tampering that overdoses chlorine (Oldsmar), and false-data injection that
  blinds the HMI while the process runs away.
- **Vendor dialects** (2): S7comm stop-CPU and mode change against the
  substation RTU, and CIP tag writes plus an unauthenticated logic push to the
  dosing controller.
- **Impact and persistence** (2): modified ladder logic that ignores the level
  sensor and holds the intake pump on, and a wiper-style HMI config clobber.

Trainees work from `docs/scenarios-trainee.md`. Instructors hold
`docs/scenarios.md`, which adds the exact exploit, the physical consequence in
the simulation, and the fix, with its CISA CPG and ISA/IEC 62443 reference, for
each one.

## Course

*Cross Creek 101* is a seven-session syllabus built on this range: orientation
and the Purdue model, exposure and access, speaking the machines' language
(Modbus), vendor dialects (S7 and CIP), securing it part one (segmentation,
allowlisting, hardening), securing it part two (monitoring, one-way
replication, secure remote access, backup and recovery), and a capstone that
chains the whole attack then locks the whole range down, followed by an
incident-response tabletop. Every command in the book was run against the
actual containers before it went to print. The ebook is at
`docs/Cross-Creek-101-Syllabus.epub`; the source is under `docs/syllabus-epub/`
and rebuilds with `docs/syllabus-epub/build-epub.sh`. The instructor kit,
`instructor/`, carries the timed agenda, the setup runbook, the grading rubric,
slide outlines, and the capstone CTF.

## Security and authorised use

Cross Creek contains deliberately vulnerable controllers, default credentials,
unauthenticated industrial protocols, and a working path to modify running
control logic, for teaching.

Use Cross Creek only: on your own machine; in a lab you control; in a classroom
or range where you have permission; under written rules of engagement for
authorised training or assessment. Never point a Cross Creek command, script,
payload, scan, or credential at a real utility, a real PLC, or any system you do
not own.

It is strictly local. Host ports bind to `127.0.0.1` only. The edge and field
networks are `internal`. `start.sh` refuses to launch if any published port
would bind beyond loopback; `status.sh` audits the running bindings and
confirms the attacker container has no default route. The attack tooling is
generic (pymodbus, pycomm3, python-snap7, nmap) and the scripts are hardcoded
to lab addresses. Keep the host offline or firewalled while the range is up.
Never deploy Cross Creek to a shared, routable, or cloud network.

## Verification

See `docs/verification.md` for the per-scenario confirmation commands, the
defended-side re-run that proves each attack now fails, and the checks that
confirm nothing is bound beyond `127.0.0.1` and the attacker box is contained.

## Project status

Training range. The scenario set, container layout, and default ports may
change between revisions. Reset the range between cohorts, several scenarios
are stateful. See `CHANGELOG.md` and `ROADMAP.md`.

## Credits

Process-simulation approach owes to GRFICS, MiniCPS, and the OpenPLC project.
Incident detail from CISA, WaterISAC, Dragos, and the EPA/AWWA water-sector
guidance. Repo conventions follow the sibling projects Widgetorium, Hack3270,
EZrecon-2, GIBSON, and DVCA.

## Acknowledgements

Built for an authorised ICS/OT security training series.

## Licence

GPL-3.0-or-later, see [`LICENSE`](LICENSE).
