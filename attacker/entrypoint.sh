#!/bin/sh
# Add the one static route the attacker box needs to reach the range through
# the boundary firewall. There is deliberately no default route: this box
# cannot reach the internet.
set -e

ROUTER="${ROUTER_EDGE_IP:-172.30.10.2}"
SUBNETS="${LAB_SUBNETS:-172.30.0.0/16}"

# reach the range only through the firewall
for net in $SUBNETS; do
  ip route replace "$net" via "$ROUTER" 2>/dev/null || true
done

# no way out: drop any default route Docker handed us and blackhole a new one
ip route del default 2>/dev/null || true
ip route add blackhole default 2>/dev/null || true

echo "[attacker] routing to the range through firewall at $ROUTER; no egress"
ip route
echo
echo "  resolver:  $(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf 2>/dev/null) (the utility's own name server)"
echo
echo "  start here:  python3 /opt/scripts/recon.py dns    # map the estate by name"
echo "              python3 /opt/scripts/recon.py sweep   # scan what DNS found"
echo "              dig axfr @172.30.10.53 crosscreek-water.lab"
echo "              nmap -Pn -sT plc-water.crosscreek-water.lab"
echo
echo "  scenario scripts:  ls /opt/scripts"
echo "  targets:  hmi-water 172.30.40.10 : hmi-power 172.30.40.11"
echo "            plc-water 172.30.40.20:502  plc-dosing 172.30.40.21:44818"
echo "            plc-power 172.30.40.22:102  eng-ws 172.30.20.20"

exec sleep infinity
