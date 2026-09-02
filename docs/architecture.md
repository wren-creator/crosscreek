# Cross Creek architecture

## Segments (Purdue model)

```
   host: 127.0.0.1 only
   +---------------------------------------------------------------------------+
   |                                                                           |
   |  edge-net 172.30.10.0/24   (the hostile "internet")                       |
   |    attacker 172.30.10.10  --- no default route (blackholed) ---+          |
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
   |                         hmi-water  .10      plc-water  .20  Modbus  502    |
   |                         hmi-power  .11      plc-dosing .21  CIP     44818  |
   |                         jumphost   .40      plc-power  .22  S7      102    |
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
| `MODBUS_WRITE_OPEN` | 3-5 | no validation; OpenPLC keyswitch in REMOTE | setpoint clamp + keyswitch locked in RUN |
| `S7_NO_PASSWORD` | 7 | stop-CPU / breaker-open unauthenticated | RTU forces RUN, ignores unauthenticated opens |
| `ENIP_ALLOW_LOGIC_DOWNLOAD` | 8 | controller in REMOTE, logic-update service on | keyswitch RUN, service returns 403 |
| `FLAT_NETWORK` | 5 | firewall forwards everything | zones + conduits enforced |
| `IDS_ENABLED` | 6 | Suricata off (no `ids` container) | on, rules loaded |
| `HISTORIAN_READONLY` | 6 | bidirectional historian link | one-way OT -> DMZ |
| `VERBOSE_HMI_ERRORS` | - | stack traces and tag map leaked | generic errors |

## Mechanics worth explaining in detail

### The dosing logic-download stand-in (scenario 8)

A true Studio 5000 download is not reproducible without Rockwell tooling.
`plc-dosing` instead runs an embedded cpppo EtherNet/IP simulator for the tag
surface (real CIP reads/writes work) plus a Flask service on :8080. A POST to
`/logic` while `ENIP_ALLOW_LOGIC_DOWNLOAD=1` sets the `LogicForced` tag; the
scan loop then pins `DoseRate` at 100% and `process-sim` treats the downstream
overdose interlock as bypassed. It teaches the concept and gives the IDS
something real to alert on; it is not the S7-of-CIP wire format.

### HMI blinding (scenario 6)

`process-sim` writes live sensor values into `plc-water` holding registers
10-15 every tick; the PLC scan loop mirrors them to input registers 0-6 for
the HMI. An attacker on `ot-net` can hold either block at a nominal value
faster than the sim updates it, so the HMI shows a healthy plant. The
segmented HMI adds a plausibility check: a value that moved faster than the
model allows is flagged rather than shown.

### Why the attacker can reach OT in flat mode but not segmented

Flat: `forward accept` + masquerade, so `attacker -> router-fw -> ot-net`
works and replies return. Segmented: `forward drop` with no edge conduit, so
the SYN is dropped at the firewall and logged; Suricata, inline on the
firewall's edge interface, still sees and alerts on the attempt.
