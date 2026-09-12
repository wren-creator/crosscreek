# Cross Creek architecture

## Segments (Purdue model)

```
   host: 127.0.0.1 only
   +---------------------------------------------------------------------------+
   |                                                                           |
   |  edge-net 172.30.10.0/24   (the hostile "internet")                       |
   |    attacker 172.30.10.10  --- no default route (blackholed) ---+          |
   |    dns      172.30.10.53   utility name server (AXFR open in flat)         |
   |                                                                |          |
   |                                            router-fw (nftables)|          |
   |  it-net 172.30.20.0/24  ------------  L3 / L3.5 boundary  ------+          |
   |    eng-ws    172.30.20.20              flat | segmented         |          |
   |    historian 172.30.20.30                                      |          |
   |                                            +------ dmz-net 172.30.30.0/24  |
   |                                            |         historian .30         |
   |                                            |         jumphost  .40 (seg.)  |
   |                                            |                               |
   |                       ot-net 172.30.40.0/24 (single flat OT segment)       |
   |                         hmi-water  .10      plc-water  .20  Modbus  10502  |
   |                         hmi-power  .11      plc-dosing .21  CIP     54818  |
   |                         jumphost   .40      plc-power  .22  S7      10102  |
   |                                                                           |
   |                       sim-net 172.30.50.0/24 (internal, the field bus)     |
   |                         process-sim .5  <->  plc-water  .10                |
   |                                              plc-dosing .11               |
   |                                              plc-power  .12               |
   +---------------------------------------------------------------------------+
```

- **All published ports bind to `127.0.0.1`.** `start.sh` refuses to launch
  otherwise; `status.sh` re-audits the running bindings.
- **`sim-net` is `internal: true`.** The field bus routes nowhere.
- **`edge-net` is not `internal`.** Marking it internal also blocks the
  attacker from routing *through* the firewall, which scenarios 1, 2 and the
  whole segmentation lesson need. Instead the attacker box holds no default
  route (its entrypoint blackholes one) and `status.sh` proves it cannot open
  a connection to a public address.
- **The OT network is one flat segment.** Most small utilities run it that
  way, and Session 5 is about fixing it. HMIs, PLCs and (in segmented mode)
  the jump host share `ot-net`; the boundary firewall is between OT and
  everything else, not inside OT.
- **None of the three PLCs sits on its IANA-assigned default port.** Modbus,
  S7comm and EtherNet/IP normally default to 502, 102 and 44818; here they run
  on 10502, 10102 and 54818 (`PLC_WATER_PORT` / `PLC_POWER_PORT` /
  `PLC_DOSING_PORT` in `.env.example`). `recon.py sweep`'s hardcoded default-
  port list finds nothing here on purpose: `recon.py nmap` does the real
  discovery, a full TCP range sweep followed by nmap's vendor NSE scripts
  (`modbus-discover`, `s7-info`, `enip-info`) for whatever free device
  name/model/firmware they can pull, though those scripts key off the
  protocol's textbook port and often just say `unknown` here; `recon.py
  registers` confirms it either way, talking the actual protocol and walking
  the coil/register/tag map once the port is known.

## The boundary firewall

`router-fw` bridges `edge-net`, `it-net`, `dmz-net` and `ot-net` and runs
nftables. `FW_MODE` (from `FLAT_NETWORK` / the segmented override) picks the
ruleset:

- **`nftables.flat.conf`**: `forward policy accept` plus `ip saddr
  172.30.0.0/16 masquerade`. The masquerade is what lets the attacker's
  replies come back: the attacker sits on `edge-net` with no route of its own,
  so its packets are SNAT'd to the firewall's address on the exit segment and
  the target replies to something it can reach.
- **`nftables.segmented.conf`**: `forward policy drop`, `ct state
  established,related accept`, then exactly three conduits: IT <-> DMZ, the DMZ
  jump host to OT on ssh/http, and the DMZ historian to OT on the read ports.
  Every other cross-zone packet hits `log prefix "CC-FW-DROP " counter drop`.

## The IDS

`ids` (Suricata 8) runs with `network_mode: service:router-fw`, so it shares
the firewall's namespace and sees all four segment interfaces. It loads only
`net/ids/rules/crosscreek.rules` (six rules, no ET Open). The `:9411` endpoint
(published on `router-fw`) tails the EVE alerts as plain text.

## Volumes

| Volume | Mounted at | Purpose |
|---|---|---|
| `historian-data` | `historian:/var/lib/historian` | recorded tag history; wiped by `stop.sh --all` / `reset.sh` |
| `ids-logs` (segmented) | `ids:/var/log/suricata` | Suricata EVE json |

## Toggles

Read from `.env` (created from `.env.example` by `setup.sh`). Every one
defaults to the vulnerable value if `.env` is absent.
`docker-compose.segmented.yml` sets them all safe at once.

| Var | Session | `1` (default) | `0` / segmented |
|---|---|---|---|
| `EXPOSE_HMI_TO_EDGE` | 2 | (documentary) HMI reachable from the edge via the flat firewall | edge -> OT dropped |
| `DEFAULT_CREDS` | 2 | HMI `admin/admin`, PLC pass `1100` | operator-set credentials |
| `EXPOSE_REMOTE_ACCESS` | 2 | unauthenticated VNC-style port on `eng-ws` | remote access via the DMZ jump host only |
| `DNS_AXFR_OPEN` | 2 | name server answers for the whole estate, zone transfer open to any client | split-horizon public view only, AXFR refused |
| `MODBUS_WRITE_OPEN` | 3-5 | no validation; OpenPLC keyswitch in REMOTE | release-limit and setpoint clamps + keyswitch locked in RUN |
| `S7_NO_PASSWORD` | 7 | stop-CPU / breaker-open unauthenticated | RTU forces RUN, ignores unauthenticated opens |
| `ENIP_ALLOW_LOGIC_DOWNLOAD` | 8 | controller in REMOTE, logic-update service on | keyswitch RUN, service returns 403 |
| `FLAT_NETWORK` | 5 | firewall forwards everything | zones + conduits enforced |
| `IDS_ENABLED` | 6 | Suricata off (no `ids` container) | on, rules loaded |
| `HISTORIAN_READONLY` | 6 | bidirectional historian link | one-way OT -> DMZ |
| `VERBOSE_HMI_ERRORS` | - | stack traces and tag map leaked | generic errors |

## The name server

`dns` is CoreDNS, authoritative-only, no recursion and no upstream (offline
like the rest of the range). It sits on `edge-net` at `172.30.10.53` with the
attacker box, so the attacker queries it directly with no firewall in the
path, the same way an external assessor queries a target's public name
server. The `attacker` service points its `dns:` / `dns_search:` at it, so
`nmap plc-water` and `dig axfr @172.30.10.53 crosscreek-water.lab` both work
out of the box.

`DNS_AXFR_OPEN` (from the segmented override) picks one of two full config
sets the same way `router-fw` picks its nftables ruleset:

- **flat (`1`)**: `Corefile.flat` plus the `.flat` zone files. Forward zones
  for `crosscreek-water.lab` and `crosscreek-power.lab` with an A record for
  every asset, a `scada` / `rtu` CNAME, a `www` / `vpn` / `mail` public
  presence, an SPF-style TXT breadcrumb, and a `30.172.in-addr.arpa` reverse
  zone that names the OT `/24`. Every zone has `transfer { to * }`, so
  `dig axfr` from anywhere returns the lot. This is scenario 11.
- **segmented (`0`)**: `Corefile.segmented` plus the `.segmented` zone files.
  Split-horizon: only `ns1` / `www` / `vpn` / `mail` resolve, the OT and
  engineering records and the OT PTRs are gone, and there is no `transfer`
  block so AXFR returns `REFUSED`. From the edge, `plc-water.crosscreek-water.lab`
  is `NXDOMAIN` and `nmap -sL` on the OT range returns bare addresses.

Both "utilities" resolve `eng-ws` and `historian` to the same hosts: the zone
transfer is where a student learns the water plant and the substation share an
engineering workstation and a historian.

## Mechanics worth explaining in detail

### The water plant: a two-pass RO demineralisation train

`plc-water` runs an OpenPLC-style program for a reverse-osmosis ultrapure
water plant: feed and antiscalant dosing, RO pass 1, NaOH inter-pass dosing,
RO pass 2, a DI storage tank (3B401), a recirculating distribution loop with a
circulation pump (3P401) and a UV steriliser (3UV401), and a release interlock
("Release to Consumers") that only permits release when RO2 and loop-return
conductivity are below `HR_COND_LIMIT_US`, UV intensity is above threshold, and
the tank is not empty. `process-sim/model_water.py` models the coupling: cut
the antiscalant and the membranes foul (RO1 conductivity climbs, RO2 follows);
cut the NaOH inter-pass dose and CO2 breaks through (RO2 conductivity climbs);
stop the loop pump and the pressure bleeds out. The full Modbus map is in
`plc/water-openplc/mapfile.py`.

### The dosing logic-download stand-in (scenario 8)

A true Studio 5000 download is not reproducible without Rockwell tooling.
`plc-dosing` (the NaOH inter-pass dosing controller) instead runs an embedded
cpppo EtherNet/IP simulator for the tag surface (real CIP reads/writes work)
plus a Flask service on :8080. A POST to `/logic` while
`ENIP_ALLOW_LOGIC_DOWNLOAD=1` sets the `LogicForced` tag; the scan loop then
pins `DoseRate` at 100% and `process-sim` adds a contaminant term to the loop
return conductivity. It teaches the concept and gives the IDS something real to
alert on; it is not the CIP wire format for a program download.

### HMI blinding (scenario 6)

`process-sim` writes live sensor values into `plc-water` holding registers
10-22 every tick; the PLC scan loop mirrors them to input registers 0-14 for
the HMI. An attacker on `ot-net` can hold either block at a nominal value
faster than the sim updates it, so the HMI shows RO2 conductivity at spec and
Release green while the loop circulates off-spec water. The segmented HMI adds
a plausibility check: a value that moved faster than the model allows is
flagged rather than shown.

### Why the attacker can reach OT in flat mode but not segmented

Flat: `forward accept` + masquerade, so `attacker -> router-fw -> ot-net`
works and replies return. Segmented: `forward drop` with no edge conduit, so
the SYN is dropped at the firewall and logged; Suricata, inline on the
firewall's edge interface, still sees and alerts on the attempt.
