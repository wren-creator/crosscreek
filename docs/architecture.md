# Cross Creek architecture

> Stub. Filled in once the network boundary and all service images land. The
> segment map, address plan, and toggle table below are authoritative for the
> build.

## Segments (Purdue model)

```
   host: 127.0.0.1 only
   ┌───────────────────────────────────────────────────────────────────────┐
   │                                                                       │
   │  edge-net 172.30.10.0/24  (internal, no internet)                     │
   │    attacker 172.30.10.10 ───┐                                         │
   │                             │                                         │
   │                      ┌──────▼───────┐  router-fw                      │
   │  enterprise-net ─────┤  L3 / L3.5   ├───── dmz-net 172.30.30.0/24     │
   │  172.30.20.0/24      │  boundary    │        historian 172.30.30.30   │
   │    eng-ws .20        │  firewall    │        jumphost .40 (segmented) │
   │    historian .30     │  nftables    │                                 │
   │                      │ flat|segmented│                                │
   │                      └──┬────────┬──┘                                 │
   │            ot-hmi-net   │        │   ot-plc-net 172.30.41.0/24        │
   │            172.30.40.0/24        │     plc-water   .10  Modbus :502   │
   │              hmi-water .10       │     plc-dosing  .11  CIP    :44818 │
   │              hmi-power .11       │     plc-power   .12  S7     :102   │
   │                                 │                                     │
   │                     sim-net 172.30.50.0/24  (internal)               │
   │                       process-sim .5  <->  plc-water .10             │
   │                                            plc-dosing .11            │
   │                                            plc-power .12             │
   └───────────────────────────────────────────────────────────────────────┘
```

- **All published ports bind to `127.0.0.1`.** `start.sh` refuses to launch
  otherwise; `status.sh` audits the running bindings.
- **`edge-net` and `sim-net` are `internal: true`.** Nothing on them routes to
  the host LAN or the internet. The attacker box is only on `edge-net`, so it
  has no default route; it reaches the other segments (when the firewall lets
  it) via a static route through `router-fw` at `172.30.10.2`. This is the same
  `internal: true` caveat noted in Widgetorium: on some Docker releases it also
  suppresses host port publishing, which is why the OT nets that publish HMI and
  PLC ports are *not* marked internal.
- **HMIs and PLCs are on different subnets** (`ot-hmi-net` vs `ot-plc-net`) so
  that `router-fw` is genuinely in the path between them. That is what makes the
  Session 5 protocol allowlist a real control and not a no-op.

## Volumes

| Volume | Mounted at | Purpose |
|---|---|---|
| `historian-data` | `historian:/var/lib/historian` | recorded tag history; wiped by `stop.sh --all` / `reset.sh` |
| `ids-logs` (segmented) | `ids:/var/log/suricata` | Suricata EVE json |

## Toggles

Read from `.env` (created from `.env.example` by `setup.sh`). Every one defaults
to the vulnerable value if `.env` is absent. `docker-compose.segmented.yml`
sets them all to the safe value at once.

| Var | Session | `1` (default) | `0` / segmented |
|---|---|---|---|
| `EXPOSE_HMI_TO_EDGE` | 2 | water HMI + PLC reachable from the edge via the flat firewall | edge → OT dropped |
| `DEFAULT_CREDS` | 2 | HMI `admin/admin`, PLC pass `1100` | operator-set credentials |
| `EXPOSE_REMOTE_ACCESS` | 2 | unauthenticated VNC-style service on `eng-ws` | remote access via DMZ jump host only |
| `MODBUS_WRITE_OPEN` | 3 | writes accepted from any source | PLC-side source allowlist |
| `S7_NO_PASSWORD` | 4 | stop-CPU / mode change unauthenticated | auth required |
| `ENIP_ALLOW_LOGIC_DOWNLOAD` | 4 | controller in REMOTE/PROG, logic-update service on | keyswitch in RUN, service off |
| `FLAT_NETWORK` | 5 | router forwards everything | zones + conduits enforced |
| `IDS_ENABLED` | 6 | Suricata/Zeek off | on, rules loaded |
| `HISTORIAN_READONLY` | 6 | bidirectional historian link | one-way OT → DMZ |
| `VERBOSE_HMI_ERRORS` | — | stack traces and tag names leaked | generic errors |

## Mechanics worth explaining in detail

_To be written as each scenario is proven against the running range: the
logic-download stand-in on the dosing controller, the HMI-blinding replay, and
the flat-vs-segmented firewall path._
