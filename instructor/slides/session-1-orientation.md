# Session 1 — Orientation and the Purdue Model

## Slide 1: Two headlines
- Aliquippa, PA, Nov 2023: internet-exposed PLC, password `1111`, CyberAv3ngers
- Lviv, Jan 2024: FrostyGoop, plain Modbus, 600 buildings cold for 2 days
- Neither was clever. That is the point.

## Slide 2: The line you do not cross
- ICS output = pump, valve, breaker, chemical feed
- No forgiving failure mode. A stopped CPU can overflow a tank into a river.
- Rule: your equipment, a purpose-built range, or a signed RoE with an engineer standing by. Nothing else.
- "Just a scan" and "just reading" are not exceptions.

## Slide 3: Bring it up, prove it is contained
- `./setup.sh && ./start.sh && ./status.sh`
- status.sh checks: loopback-only ports, attacker has no internet, no stray binds
- Build the "prove my traffic stayed in scope" reflex here

## Slide 4: The Purdue model
- L4/5 enterprise · L3.5 DMZ · L3 eng-ws/historian · L2 HMI · L1 PLC · L0 process
- Cross Creek: L1 and L2 share one flat `ot-net` — like most real small utilities
- Every Session 5–7 decision is an argument about which level something belongs on

## Slide 5: Map the plant by hand
- Both HMIs as an operator; then `recon.py sweep` from the attacker box
- Write down: 3 ICS protocols, 2 HMIs, eng-ws one hop away, a curious :8080 on the dosing controller
- You built the map, not a tool

## Slide 6: What you should notice
- Nothing asked you for a credential
- Modbus / EtherNet/IP / S7comm: all predate auth-on-a-control-network
- The plant's entire security model right now is "the bad guys can't get here"
