# Session 2 — Exposure and Access

## Slide 1: Start with the name (scenario 11)
- Real assessments start from a domain, not an IP
- Utility name server on the edge: `172.30.10.53`, answers for the whole estate, AXFR open
- `recon.py dns` → zone transfer of `crosscreek-water.lab` + `crosscreek-power.lab` + reverse sweep
- Payoff: every controller named by function, no packets to the PLCs; both plants share `eng-ws` + `historian`
- By hand: `dig axfr @172.30.10.53 crosscreek-water.lab`, `nmap -Pn -sL 172.30.40.0/24`

## Slide 2: The Aliquippa pattern
- Controller/HMI reachable from the internet + factory credential
- CISA advisory fix: "disconnect it, change the password" — not a patch
- Cross Creek: water HMI reachable from the edge in flat mode

## Slide 3: Do it
- `recon.py creds` → `admin/admin -> ACCEPTED`
- Browser → `http://127.0.0.1:8071` → log in → you are an operator
- Take 3P401 to HAND and stop it, watch the loop pressure fall

## Slide 4: The Oldsmar pattern
- Feb 2021: operator watched the mouse move; lye setpoint 100 → 11,100 ppm
- Way in: a reachable, unauthenticated remote-access tool
- Cross Creek: `nc -v 172.30.20.20 5900` → "no authentication configured"

## Slide 5: The workstation is the prize
- `recon.py engws` → `notes.txt`: every controller address + password + keyswitch state
- Also serves `water_plc.st`, the golden program (you modify it in Session 4)
- Every real assessment finds this file. It is always `notes.txt` or `passwords.xlsx`.

## Slide 6: Map to ATT&CK for ICS
- T0888 Remote System Information Discovery · T0846 Remote System Discovery
- T0883 Internet Accessible Device · T0812 Default Credentials
- T0822 External Remote Services · T0818 Engineering Workstation Compromise

## Slide 7: What you should notice
- You exploited nothing
- Name server that talked + exposed service + unchanged commissioning password + open share
- That is the entire 2021–2024 public water-sector record
