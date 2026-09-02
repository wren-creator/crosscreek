"""Lab addresses. Every attack script imports these so nothing here can be
pointed at an address that is not Cross Creek."""

HMI_WATER = "172.30.40.10"
HMI_POWER = "172.30.40.11"
PLC_WATER = "172.30.40.20"      # Modbus/TCP 502, OpenPLC UI 8080
PLC_DOSING = "172.30.40.21"     # EtherNet/IP 44818, logic-update 8080
PLC_POWER = "172.30.40.22"      # S7comm 102
ENG_WS = "172.30.20.20"
OT_SUBNET = "172.30.40."        # /24

MODBUS_PORT = 502
ENIP_PORT = 44818
S7_PORT = 102
HTTP_PORT = 8080


def guard(host):
    if not host.startswith("172.30."):
        raise SystemExit(f"refusing: {host} is not a Cross Creek lab address")
    return host
