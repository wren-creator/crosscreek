# Cross Creek verification runbook

> Stub. Section B fills in one row per scenario as each is proven. Sections A,
> C, and D are structurally complete.

## Section A, containment (run first and last, every session)

| # | Command | Pass condition |
|---|---|---|
| A1 | `./status.sh` | exits 0; "audit clean" line printed |
| A2 | `docker compose ps --format '{{.Name}}\t{{.Ports}}'` | every mapping reads `127.0.0.1:` |
| A3 | `docker exec crosscreek-attacker ip route` | no `default` route present |
| A4 | `docker exec crosscreek-attacker sh -c 'getent hosts example.com && curl -m5 -sI http://example.com'` | both fail (no DNS, no route) |
| A5 | from another machine on your LAN: `nmap -Pn -p 8071,8072,5020,4840,1020 <this-host-ip>` | all filtered or closed |

## Section B, per-scenario (attack side, flat topology)

_One row per scenario, filled in as the matching service image lands. Shape:_

| # | Steps | Pass condition |
|---|---|---|
| B1 | _TBD_ | _TBD_ |

## Section C, reset

| # | Command | Pass condition |
|---|---|---|
| C1 | `./reset.sh -y` | completes; range healthy |
| C2 | water HMI shows nominal levels, chlorine setpoint back to default | yes |
| C3 | `plc-water` logic is the golden program (no attacker ladder changes) | yes |
| C4 | historian rows cleared | yes |

## Section D, defended side

| # | Command | Pass condition |
|---|---|---|
| D1 | `./start.sh --segmented` | comes up healthy, `crosscreek-ids` running |
| D2 | re-run each Group A script from `attacker` | A1/A2 targets unreachable (firewall drop) |
| D3 | re-run each Group B/C script from `attacker` | writes rejected; connection refused or dropped |
| D4 | `curl -s http://127.0.0.1:9411/` (or tail `ids-logs`) | one Suricata alert per attempt above |
| D5 | trigger the Group B6 blind from a sanctioned host | HMI plausibility check flags the mismatch |
| D6 | `docker exec crosscreek-historian sh -c 'nc -zv 172.30.41.10 502'` with `HISTORIAN_READONLY=1` | refused (one-way link) |

## Section E, ebook

| # | Command | Pass condition |
|---|---|---|
| E1 | `cd docs/syllabus-epub && ./build-epub.sh` | `mimetype` listed first and stored (method `stored`) |
| E2 | `epubcheck docs/Cross-Creek-101-Syllabus.epub` (if installed) | no errors |
