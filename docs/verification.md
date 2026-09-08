# Cross Creek verification runbook

End-to-end checks. Section A is containment, run it first and last every
session. Section B walks the attack side (flat topology). Section D is the
defended re-run. All attacker commands are run inside `crosscreek-attacker`
(`docker exec -it crosscreek-attacker bash`).

## Section A, containment (run first and last)

| # | Command | Pass condition |
|---|---|---|
| A1 | `./status.sh` | exits 0; prints "audit clean" |
| A2 | `docker compose ps --format '{{.Name}}\t{{.Ports}}'` | every published mapping reads `127.0.0.1:` |
| A3 | `docker exec crosscreek-attacker ip route` | default route is `blackhole` |
| A4 | `docker exec crosscreek-attacker python3 -c 'import socket;print(socket.socket().connect_ex(("1.1.1.1",53)))'` | non-zero (unreachable) |
| A5 | from another machine on your LAN: `nmap -Pn -p 8071,8072,5020,4840,1020 <this-host-ip>` | all filtered or closed |

## Section B, per-scenario (attack side, `./start.sh`)

| # | Steps | Pass condition |
|---|---|---|
| B0 | `python3 /opt/scripts/recon.py dns` | AXFR of `crosscreek-water.lab` and `crosscreek-power.lab` succeeds and lists every HMI/PLC/eng-ws by name; reverse sweep names .40.10/.11/.20/.21/.22. `dig axfr @172.30.10.53 crosscreek-water.lab` returns the zone. `nmap -Pn -sT plc-water.crosscreek-water.lab` shows 502/8080 open. |
| B1 | `python3 /opt/scripts/recon.py sweep` then `recon.py creds` | sweep resolves the named hosts and lists 172.30.40.10/.11/.20/.21/.22 with their ICS ports; creds prints `admin/admin -> ACCEPTED` for both HMIs |
| B2 | `nc -v 172.30.20.20 5900` | connects; banner says "no authentication configured" |
| B3 | `python3 /opt/scripts/recon.py engws` | prints `notes.txt` with the controller passwords and `water_plc.st` |
| B4 | `python3 /opt/scripts/modbus_attack.py stop-loop`; watch water HMI 3PITC401 | loop pressure falls from 3.8 bar toward 0; `DI_LOOP_PRESS_LOW` latches within a few seconds |
| B5 | `python3 /opt/scripts/modbus_attack.py raise-limit 5.0` then `starve-antiscalant`; watch 1QAH301 / 2QAH401 | RO1 conductivity climbs 12 -> 50 uS/cm over ~30 s, RO2 follows past 2 uS/cm, but `DI_COND_HIGH_RO2` does NOT trip and Release stays green (limit defeated). Without the raised limit, Release drops. |
| B6 | run B5 (no raised limit) while a `pymodbus` loop re-writes IR 3 and IR 6-9 to nominal | water HMI shows RO2 ~0.5 uS/cm and Release green while the process is actually off-spec |
| B7 | `python3 /opt/scripts/s7_attack.py trip feeder` then `trip load` | power HMI: 52-F and 52-L show OPEN; frequency climbs past 50.5 Hz; excursion alarm |
| B8 | `python3 /opt/scripts/s7_attack.py stop` | power HMI shows RTU CPU STOP; breaker commands stop taking effect |
| B9 | `python3 /opt/scripts/cip_attack.py set 15` then `cip_attack.py logic-push` | after logic-push, `cip_attack.py read` shows `LogicForced [1]`, `LogicRev` incremented; RO2 / loop-return conductivity climb past the limit, Release blocked (release the water by chaining B5 or scenario 9) |
| B10 | `python3 /opt/scripts/push_logic_water.py` | OpenPLC UI (`:8073`) shows program `crosscreek_ro_v1_PATCHED`; Release forced true regardless of conductivity or UV |
| B11 | `./reset.sh -y` | range returns to golden: setpoints nominal, `crosscreek_ro_v1 (golden)` running, alarms clear |

## Section C, reset

| # | Command | Pass condition |
|---|---|---|
| C1 | `./reset.sh -y` | completes; all containers healthy |
| C2 | water HMI: RO2 conductivity < 1 uS/cm, loop ~3.8 bar, Release green, no alarms | yes |
| C3 | OpenPLC UI `:8073` program name is `crosscreek_ro_v1 (golden)` | yes |
| C4 | `curl -s 127.0.0.1:9411` (segmented only) or historian `/recent` | fresh samples, no residual attacker state |

## Section D, defended side (`./start.sh --segmented`)

| # | Steps | Pass condition |
|---|---|---|
| D1 | `./start.sh --segmented` | comes up healthy including `crosscreek-ids` and `crosscreek-jumphost` |
| D2 | re-run B0 then B1 | B0: `dig axfr` returns `REFUSED`, `plc-water.crosscreek-water.lab` is `NXDOMAIN`, `nmap -sL 172.30.40.0/24` returns bare addresses. B1: `recon.py sweep` finds nothing; `creds` cannot reach the HMIs |
| D3 | re-run B4, B7, B9, B10 from the attacker | every attempt times out (firewall drop) |
| D4 | `docker exec crosscreek-router-fw nft list ruleset \| grep CC-FW-DROP` | drop counter is climbing |
| D5 | `curl -s http://127.0.0.1:9411/` | one alert per attempt above ("edge host reaching a PLC protocol port", etc.) |
| D6 | from `crosscreek-eng-ws`: reach a PLC only via the jump host (`ssh jumphost` then to OT) | direct eng-ws -> PLC is dropped; via jump host works |
| D7 | on the water PLC, `MODBUS_WRITE_OPEN=0`, write `HR_COND_LIMIT_US` = 5000 (50 uS/cm) from a test client | the PLC clamps it back to 500 (5.00 uS/cm) within one scan |

## Section E, ebook

| # | Command | Pass condition |
|---|---|---|
| E1 | `cd docs/syllabus-epub && ./build-epub.sh` | `mimetype` listed first and `stored` (not deflated) |
| E2 | `epubcheck docs/Cross-Creek-101-Syllabus.epub` (if installed) | no errors |
