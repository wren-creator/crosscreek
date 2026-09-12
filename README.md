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

One `docker-compose.yml` stands up a small utility: a two-pass reverse-osmosis
demineralisation plant with a recirculating DI distribution loop (feed and
antiscalant, RO1/RO2 with NaOH inter-pass dosing, a DI storage tank, a UV
steriliser, a release interlock) and a single-bus power substation, driven by
three simulated controllers that speak real protocols, Modbus/TCP, EtherNet/IP
(CIP), and S7comm. A Python process simulator plays the part of the
physical world: cut the antiscalant and the membranes foul, stop the loop pump
and the pressure bleeds out, tamper the conductivity limit and off-spec water
is released. The water HMI is styled after a STEMENS SIMATIX panel "Plant Overview";
the power HMI is a browser-based SCADA control center, single-line diagram,
alarm log, metering trends, breaker controls. A firewall container sits on the
boundary between the enterprise, DMZ, and OT segments. An attacker workstation
sits on a hostile "edge" network with no route off the lab, alongside the
utility's own name server, which in the flat topology answers for the whole
estate and lets anyone pull the zone, so recon starts from the utility name,
not a handed-over address.

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

# rebuild images first, to pick up local edits to the HMIs or other
# services without wiping lab state (flags combine: ./start.sh --segmented --build)
./start.sh --build

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
| `plc/water-openplc/` | OpenPLC runtime, the RO demineralisation plant logic, Modbus/TCP |
| `plc/dosing-enip/` | Allen-Bradley-style NaOH dosing controller, EtherNet/IP (CIP) |
| `plc/power-s7/` | STEMENS-style substation RTU, S7comm |
| `process-sim/` | the physics: RO conductivity and recovery, DI tank and loop, bus frequency, breaker state |
| `hmi/water/` `hmi/power/` | operator screens: a SIMATIX-style Plant Overview and a browser-based SCADA control center (Flask + SVG) |
| `eng-ws/` | engineering workstation, holds PLC project files and creds: the pivot box |
| `historian/` | data historian in the DMZ, one-way replication in segmented mode |
| `net/router-fw/` | the boundary firewall, `flat` and `segmented` nftables rulesets |
| `net/dns/` | the utility name server (CoreDNS), `flat` zones with open AXFR / `segmented` split-horizon |
| `net/ids/` | Suricata with ICS rules (segmented mode) |
| `attacker/` | analyst workstation: nmap, pymodbus, cpppo, python-snap7, tcpdump, scripts |
| `docs/scenarios.md` | instructor answer key: every planted weakness, exploit, physical effect, fix |
| `docs/scenarios-trainee.md` | trainee copy with the fix removed |
| `docs/architecture.md` | segments, addresses, volumes, toggles, and the tricky mechanics |
| `docs/verification.md` | end-to-end test runbook, attack side and defended side |
| `docs/syllabus-epub/` | source for *Cross Creek 101*, a seven-session syllabus |
| `docs/Cross-Creek-101-Syllabus.epub` | the built syllabus ebook (`docs/syllabus-epub/build-epub.sh`) |
| `instructor/` | timed agenda, setup runbook, grading rubric, slide outlines, capstone CTF |
| `setup.sh` `start.sh` `stop.sh` `status.sh` `reset.sh` | lifecycle scripts |

## Tools

What's actually running under the hood, protocol libraries first since
they're the part worth knowing: the simulated controllers and the attack
scripts on the other side of the wire both speak through the same three.

| Protocol | Library | Where it's used |
|---|---|---|
| Modbus/TCP | `pymodbus` | water PLC, water HMI, historian, process-sim, `modbus_attack.py` |
| EtherNet/IP (CIP) | `cpppo` | dosing PLC, process-sim, `cip_attack.py` |
| S7comm | `python-snap7` | substation RTU, power HMI, historian, process-sim, `s7_attack.py` |

Everything else:

| Tool | Role |
|---|---|
| Docker Compose | the range itself, flat and segmented topologies |
| `nftables` | the boundary firewall (`net/router-fw/`), separate flat/segmented rulesets |
| CoreDNS | the utility name server (`net/dns/`), open zone transfer in flat mode, split-horizon in segmented |
| Suricata 8 | ICS-aware IDS in segmented mode, custom rules in `net/ids/rules/` |
| `nmap`, `dig`, `tcpdump` | recon, DNS enumeration, and packet capture on the attacker workstation |
| Flask | every HMI, PLC runtime UI, and the historian's web front end |
| plain HTML/CSS/JS + inline SVG | both HMIs, no framework, no CDN, the range runs fully offline |
| `zip` | packages *Cross Creek 101* into a valid `.epub` (`docs/syllabus-epub/build-epub.sh`) |

## Services and ports

| Service | Host bind | Purpose |
|---|---|---|
| water HMI | `127.0.0.1:8071` | water plant operator screen |
| power HMI | `127.0.0.1:8072` | substation operator screen |
| water PLC (OpenPLC UI) | `127.0.0.1:8073` | runtime web UI, used for the logic-download exercise |
| water PLC (Modbus) | `127.0.0.1:5020` | Modbus/TCP, container port 10502 (off the IANA default 502, see recon below) |
| dosing PLC (CIP) | `127.0.0.1:4840` | EtherNet/IP, container port 54818 (off the IANA default 44818) |
| substation RTU (S7) | `127.0.0.1:1020` | S7comm, container port 10102 (off the IANA default 102) |
| IDS events | `127.0.0.1:9411` | Suricata EVE tail, segmented mode only |
| process-sim, historian, router-fw, eng-ws, dns | not published | internal only (the attacker reaches `dns` on `edge-net`) |

## Scenarios

Eleven planted weaknesses in four groups, each tied to a published incident and
mapped to MITRE ATT&CK for ICS:

- **Exposure and access** (4): internet-exposed HMI with default credentials
  (Aliquippa, 2023), an unauthenticated remote-access service to the OT LAN
  (Oldsmar, 2021), an engineering workstation reachable from the enterprise
  net that holds project files and PLC credentials, and a name server that
  answers for the whole estate and allows a zone transfer to any client, so
  one `dig axfr` maps every controller by name (scenario 11, the recon step
  the rest assume).
- **Protocol abuse** (3): an unauthenticated Modbus write that stops the DI
  loop circulation pump (FrostyGoop, Lviv, 2024), a holding-register write that
  raises the release conductivity limit so off-spec water passes the quality
  gate (Oldsmar, 2021), and false-data injection that blinds the HMI while the
  process runs away.
- **Vendor dialects** (2): S7comm stop-CPU and breaker trip against the
  substation RTU, and CIP tag writes plus an unauthenticated logic push to the
  NaOH dosing controller.
- **Impact and persistence** (2): a modified control program that forces the
  "Release to Consumers" release interlock permanently on, and a wiper-style
  HMI config clobber.

None of the three PLCs listens on its IANA-assigned default port, so the
recon phase isn't optional: `recon.py nmap` runs a full-range scan then tries
nmap's `modbus-discover`, `s7-info`, and `enip-info` NSE scripts for
whatever free device name/model/firmware they can pull, and `recon.py
registers` confirms it either way by talking the actual protocol, walking
the coil/register/tag map on each controller once you know the port.

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
generic (pymodbus, cpppo, python-snap7, nmap) and the scripts are hardcoded
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
