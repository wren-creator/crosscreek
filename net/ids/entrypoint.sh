#!/bin/sh
# Run Suricata across whatever interfaces the shared (router-fw) namespace has,
# using only the Cross Creek rule file, then serve the EVE tail on :9411.
set -e

IFACES=$(ip -o link show 2>/dev/null | awk -F': ' '$2 !~ /lo|gre|tunl|vti|sit|ip6|erspan|bond/ {print $2}' | sed 's/@.*//')
[ -z "$IFACES" ] && IFACES="eth0 eth1 eth2 eth3"
ARGS=""
for i in $IFACES; do ARGS="$ARGS -i $i"; done
echo "[ids] suricata on:$ARGS"

mkdir -p /var/log/suricata
# -S loads ONLY our rule file (no ET Open download needed).
# shellcheck disable=SC2086
suricata --set outputs.1.eve-log.filename=/var/log/suricata/eve.json \
         -S /etc/suricata/rules/crosscreek.rules $ARGS >/var/log/suricata/stdout.log 2>&1 &

sleep 3
exec python3 /opt/evetail.py
