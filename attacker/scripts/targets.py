"""Lab addresses. Every attack script imports these so nothing here can be
pointed at an address that is not Cross Creek."""

import os
import socket

HMI_WATER = "172.30.40.10"
HMI_POWER = "172.30.40.11"
PLC_WATER = "172.30.40.20"      # Modbus/TCP, OpenPLC UI 8080
PLC_DOSING = "172.30.40.21"     # EtherNet/IP, logic-update 8080
PLC_POWER = "172.30.40.22"      # S7comm
ENG_WS = "172.30.20.20"
HISTORIAN = "172.30.20.30"
OT_SUBNET = "172.30.40."        # /24

# None of these sits on its IANA-assigned default (Modbus 502, S7comm 102,
# EtherNet/IP 44818), that's the point. `recon.py sweep` still checks the
# defaults, on purpose, to show that assuming them finds nothing; use
# `recon.py nmap` to actually discover what's listening.
MODBUS_PORT = int(os.environ.get("PLC_WATER_PORT", "10502"))
ENIP_PORT = int(os.environ.get("PLC_DOSING_PORT", "54818"))
S7_PORT = int(os.environ.get("PLC_POWER_PORT", "10102"))
HTTP_PORT = 8080

# The utility's own DNS. In the flat range this name server answers for the
# whole estate and allows zone transfers (scenario 11); in the segmented range
# it serves a split-horizon public view only.
DNS_SERVER = "172.30.10.53"
WATER_DOMAIN = "crosscreek-water.lab"
POWER_DOMAIN = "crosscreek-power.lab"
REVERSE_ZONE = "30.172.in-addr.arpa"

# short name -> fully qualified name, for recon by utility name
HOSTS = {
    "hmi-water":  f"hmi-water.{WATER_DOMAIN}",
    "scada":      f"scada.{WATER_DOMAIN}",
    "plc-water":  f"plc-water.{WATER_DOMAIN}",
    "plc-dosing": f"plc-dosing.{WATER_DOMAIN}",
    "hmi-power":  f"hmi-power.{POWER_DOMAIN}",
    "plc-power":  f"plc-power.{POWER_DOMAIN}",
    "rtu":        f"rtu.{POWER_DOMAIN}",
    "eng-ws":     f"eng-ws.{WATER_DOMAIN}",
    "historian":  f"historian.{WATER_DOMAIN}",
}


def guard(host):
    if not host.startswith("172.30."):
        raise SystemExit(f"refusing: {host} is not a Cross Creek lab address")
    return host


def resolve(name):
    """Resolve a lab hostname to an address, then run it through guard() so a
    poisoned or wildcard record still cannot point a script off the range."""
    try:
        ip = socket.gethostbyname(name)
    except OSError as exc:
        raise SystemExit(f"refusing: cannot resolve {name} ({exc})")
    return guard(ip)
