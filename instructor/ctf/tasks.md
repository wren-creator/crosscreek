# Cross Creek 101 CTF — tasks

Flags 1–6 are on the flat range (`./start.sh`). Flags 7–8 need the segmented
range (`./start.sh --segmented`). Work from the attacker box unless told
otherwise: `docker exec -it crosscreek-attacker bash`.

## flag1 — the open door
Log into the water HMI. What password worked for the `admin` account?

## flag2 — the loot file
Read the file the engineering workstation shares that lists the controller
credentials. What is its filename (just the name, not the path)?

## flag3 — the hard limit
`modbus_attack.py raise-limit` lets you move the release conductivity limit,
but the golden program also has a *hard* limit that stops RO pass 2 on grossly
off-spec permeate, and that one is a constant, not a register. What is it, in
uS/cm, to one decimal place? (Look in `plc/water-openplc/mapfile.py`.)

## flag4 — the patched program
Run `push_logic_water.py`. Open the water PLC runtime console (`:8073`) and read
the name of the program that is now running. Give it exactly.

## flag5 — the revision counter
Run the CIP logic push against the dosing controller. Run `cip_attack.py read`
afterward. What integer does `LogicRev` show?

## flag6 — the islanded frequency
On the flat range, trip the feeder breaker and the load breaker on the
substation. Watch the power HMI. The frequency ramps until it is clamped. What
value, in Hz, does it settle at? (Whole number.)

## flag7 — the wall (segmented)
On the segmented range, run `recon.py sweep` from the attacker box, then read
the firewall drop counter:
`docker exec crosscreek-router-fw nft list ruleset | grep CC-FW-DROP`
Is the counter zero or non-zero? Answer `zero` or `nonzero`.

## flag8 — the alert (segmented)
On the segmented range, run any Session 3 or 4 attack from the attacker box,
then `curl -s http://127.0.0.1:9411/`. Copy the bracketed signature text of the
first alert line, exactly as shown between the square brackets.
