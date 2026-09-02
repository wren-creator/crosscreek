#!/bin/sh
# router-fw entrypoint. Loads the flat or segmented nftables ruleset by FW_MODE
# and then idles. The image is also reused as the DMZ jump host, which overrides
# the entrypoint to run sshd instead.
set -e

sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true

MODE="${FW_MODE:-1}"
if [ "$MODE" = "1" ]; then
  CONF=/etc/nftables.flat.conf
  echo "[router-fw] FLAT: forwarding all inter-segment traffic"
else
  CONF=/etc/nftables.segmented.conf
  echo "[router-fw] SEGMENTED: enforcing zones and conduits"
fi

nft -f "$CONF"
echo "[router-fw] ruleset loaded from $CONF"
nft list ruleset || true

# keep the container (and its network namespace, which the ids shares) alive
exec sleep infinity
