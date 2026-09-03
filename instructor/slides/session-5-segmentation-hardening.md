# Session 5 — Now Secure It, Part One

## Slide 1: Flip the range
- `./stop.sh && ./start.sh --segmented && ./status.sh`
- Firewall → zones/conduits, every weakness toggle safe, IDS up, DMZ jump host up
- Do it all at once; understand each control on its own

## Slide 2: D1 — Segment the network
- `nftables.segmented.conf`: forward policy DROP
- Three conduits only: IT↔DMZ, jump host→OT (ssh/http), historian→OT (read ports)
- Edge (attacker) network: no conduit at all
- Denied cross-zone packet → `log prefix "CC-FW-DROP" counter drop`
- Re-run `recon.py sweep` → nothing; drop counter climbs

## Slide 3: D2 — Allowlist at the controller
- Segmentation stops the outside attacker; not the pivoted one
- `MODBUS_WRITE_OPEN=0`: PLC accepts writes only from HMI + sim, clamps the release conductivity limit (0.5–5.0) and the loop-pressure SP every scan
- Dosing controller leaves REMOTE; RTU requires auth for stop/breaker-open
- Defense in depth = 62443 conduit enforcement + defensive coding

## Slide 4: D3 — Harden the controllers
| Control | Stops | CPG |
|---|---|---|
| Keyswitch → RUN | program downloads (8, 9) | 1.E, 2.A |
| S7 station password | unauth stop / breaker-open (7) | 2.A |
| Per-operator HMI accounts | the Aliquippa login (1) | 2.A, 2.C |
| Generic errors | recon from an error page | 2.S |

## Slide 5: Re-run the attacks
- `push_logic_water.py` → "Keyswitch is in RUN. Downloads disabled."
- `cip_attack.py logic-push` → 403
- `s7_attack.py stop` → RTU back to RUN immediately

## Slide 6: What you should notice
- Every Day 1 attack times out or is refused — and you patched no protocol
- You changed who can talk to what and made the controllers stop trusting the network
- Session 6: seeing, surviving, recovering
