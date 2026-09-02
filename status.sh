#!/usr/bin/env bash
# Health, reachability, the loopback bind audit, and a containment check that
# the attacker box has no route off the lab.
set -uo pipefail
cd "$(dirname "$0")"
source ./lib.sh

require_docker

# Match whatever is actually running (flat or segmented).
FILES=(-f docker-compose.yml)
if dc -f docker-compose.yml -f docker-compose.segmented.yml ps --format '{{.Name}}' 2>/dev/null \
     | grep -q crosscreek-ids; then
  FILES+=(-f docker-compose.segmented.yml)
fi

info "containers"
dc "${FILES[@]}" ps

echo
info "endpoint checks"
for pair in \
  "water HMI|http://127.0.0.1:8071/health" \
  "power HMI|http://127.0.0.1:8072/health"; do
  label="${pair%%|*}"; url="${pair#*|}"
  code="$(curl -fsS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  [ "$code" = "200" ] && ok "$label  ($code)" || bad "$label  ($code)"
done
for pair in \
  "water PLC  Modbus|127.0.0.1|5020" \
  "dosing PLC CIP|127.0.0.1|4840" \
  "substation RTU S7|127.0.0.1|1020"; do
  label="${pair%%|*}"; host="$(echo "$pair" | cut -d'|' -f2)"; port="$(echo "$pair" | cut -d'|' -f3)"
  if (exec 3<>"/dev/tcp/$host/$port") 2>/dev/null; then ok "$label  ($host:$port open)"; exec 3>&- || true
  else bad "$label  ($host:$port closed)"; fi
done

echo
info "loopback bind audit"
AUDIT_FAIL=0
while read -r name ports; do
  [ -z "$ports" ] && continue
  if printf '%s' "$ports" | grep -Eq '(^|[, ])0\.0\.0\.0:|(^|[, ])\[?::\]?:|(^|[, ])\*:'; then
    bad "$name exposes a non-loopback binding: $ports"
    AUDIT_FAIL=1
  else
    ok "$name  $ports"
  fi
done < <(dc "${FILES[@]}" ps --format '{{.Name}}\t{{.Ports}}' 2>/dev/null)

echo
info "containment check: attacker box must not route off the lab"
if dc "${FILES[@]}" ps --format '{{.Name}}' 2>/dev/null | grep -q crosscreek-attacker; then
  if dc "${FILES[@]}" exec -T attacker sh -c 'ip route | grep -q default' 2>/dev/null; then
    bad "attacker container has a default route: it can reach the internet, stop the range"
    AUDIT_FAIL=1
  else
    ok "attacker container has no default route"
  fi
else
  warn "attacker container not running, skipped"
fi

echo
if [ "$AUDIT_FAIL" -eq 0 ]; then
  ok "audit clean: range is loopback-only and the attacker box is boxed in"
else
  bad "audit FAILED: something is reachable it should not be, stop the range"
fi

[ "$AUDIT_FAIL" -eq 0 ] || exit 1
