#!/bin/sh
# Pick the flat or segmented DNS posture the same way router-fw picks its
# nftables ruleset: one full config file per mode, selected by an env var.
set -e

WORK=/etc/coredns/active
mkdir -p "$WORK"

if [ "${DNS_AXFR_OPEN:-1}" = "1" ]; then
  MODE="flat"
  echo "[dns] flat: full forward + reverse zones, AXFR open to the world"
else
  MODE="segmented"
  echo "[dns] segmented: split-horizon public view only, AXFR refused"
fi

cp "/etc/coredns/Corefile.$MODE" "$WORK/Corefile"
for z in /etc/coredns/zones/*."$MODE"; do
  base="$(basename "$z" ".$MODE")"
  cp "$z" "$WORK/$base"
done

echo "[dns] serving:"
ls -1 "$WORK" | sed 's/^/  /'

exec coredns -conf "$WORK/Corefile"
