# Session 6 — Now Secure It, Part Two

## Slide 1: D4 — ICS-aware monitoring
- One Suricata sensor sharing the firewall's namespace → sees every segment
- Six rules (`crosscreek.rules`) — OT traffic is narrow, so few rules cover the set
- Flags: edge→PLC port, ICS protocol from a non-HMI, the two download paths
- `curl -s http://127.0.0.1:9411/` — alerts land within ~2 s
- CISA CPG 3.A. Real deployment ships to a SIEM; `:9411` is the mechanism without one.

## Slide 2: D5 — Integrity and one-way data
- Segmented HMI adds a plausibility check: a value that moved faster than physics is flagged
- `HISTORIAN_READONLY=1` + firewall permits only read ports → historian can't be a route back
- Compare HMI vs historian → divergence is the alarm that catches blinding

## Slide 3: D6 — Secure remote access
- Unauth :5900 gone (`EXPOSE_REMOTE_ACCESS=0`)
- DMZ jump host: engineer → jump host (auth) → HMI network only, never PLCs directly
- Firewall enforces: eng-ws→PLC dropped; via jump host works
- Oldsmar/Aliquippa guidance: no direct inbound to OT, terminate in the DMZ, MFA (CPG 2.H)

## Slide 4: D7 — Backup and recovery
- Scenario 9 deleted a safety interlock. Only a known-good copy undoes that.
- `./reset.sh -y` = the recovery drill: reload golden program, reset setpoints, clear historian
- Real site: offline, version-controlled, signed copies; documented restore; test the restore (CPG 7.A)
- The uncomfortable question: if your integrator vanished, do you have your own PLC program?

## Slide 5: The seven controls
- Segment · allowlist · lock the keyswitch · set the password · watch the traffic · keep an honest record · terminate remote in a DMZ · golden backup + tested restore

## Slide 6: What you should notice
- None of it is exotic. Aliquippa and Lviv had done none of it.
- Do all seven and you are no longer low-hanging fruit — and you can recover
