# Session 2 — Exposure and Access

## Slide 1: Start with the name (scenario 11)
- Real assessments start from a domain, not an IP
- Utility name server on the edge: `172.30.10.53`, answers for the whole estate, AXFR open
- `recon.py dns` → zone transfer of `crosscreek-water.lab` + `crosscreek-power.lab` + reverse sweep
- Payoff: every controller named by function, no packets to the PLCs; both plants share `eng-ws` + `historian`
- By hand: `dig axfr @172.30.10.53 crosscreek-water.lab`, `nmap -Pn -sL 172.30.40.0/24`

## Slide 2: Don't assume the port
- None of the three PLCs sits on its IANA default (Modbus 502, S7comm 102, EtherNet/IP 44818)
- `recon.py sweep` checks the defaults anyway, on purpose: it finds nothing, that's the lesson
- `recon.py nmap` → full-range TCP scan, then tries `modbus-discover` / `s7-info` / `enip-info` NSE scripts on whatever answers
- Those scripts key off the *default* port; on a moved one they usually say `unknown`, that's expected, not a dead end
- By hand: `nmap -Pn -sS -p- --min-rate 2000 <host>` (attacker box carries `NET_RAW`) then `nmap -Pn -sV --script modbus-discover,s7-info,enip-info -p<port> <host>`
- Payoff either way: an open-port map with zero coil or tag writes; confirmed identification is Slide 7

## Slide 3: The Aliquippa pattern
- Controller/HMI reachable from the internet + factory credential
- CISA advisory fix: "disconnect it, change the password", not a patch
- Cross Creek: water HMI reachable from the edge in flat mode

## Slide 4: Do it
- `recon.py creds` → `admin/admin -> ACCEPTED`
- Browser → `http://127.0.0.1:8071` → log in → you are an operator
- Take 3P401 to HAND and stop it, watch the loop pressure fall

## Slide 5: The Oldsmar pattern
- Feb 2021: operator watched the mouse move; lye setpoint 100 → 11,100 ppm
- Way in: a reachable, unauthenticated remote-access tool
- Cross Creek: `nc -v 172.30.20.20 5900` → "no authentication configured"

## Slide 6: The workstation is the prize
- `recon.py engws` → `notes.txt`: every controller address + password + keyswitch state
- Also serves `water_plc.st`, the golden program (you modify it in Session 4)
- Every real assessment finds this file. It is always `notes.txt` or `passwords.xlsx`.

## Slide 7: Registers confirm what nmap couldn't
- `recon.py registers` → `plc-water`'s coils/registers, `plc-power`'s raw DB1 bytes, `plc-dosing`'s CIP tags
- Talks the real protocol directly, no generic-scanner heuristics, so it works whether or not the NSE scripts fired on Slide 2
- Modbus and S7 are numeric with no data dictionary; the names come from `notes.txt` and `water_plc.st`, not the wire
- This is the bridge into Session 3 and 4: you now have address, protocol, and enough of a point map to write against

## Slide 8: Map to ATT&CK for ICS
- T0888 Remote System Information Discovery · T0846 Remote System Discovery
- T0883 Internet Accessible Device · T0812 Default Credentials
- T0822 External Remote Services · T0818 Engineering Workstation Compromise

## Slide 9: What you should notice
- You exploited nothing
- Name server that talked + exposed service + unchanged commissioning password + open share
- That is the entire 2021–2024 public water-sector record
