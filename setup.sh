#!/usr/bin/env bash
# One-time setup: preflight checks, build images. Safe to re-run.
set -uo pipefail
cd "$(dirname "$0")"
source ./lib.sh

require_docker

# Host ports the range publishes (all on 127.0.0.1). If any is already taken
# the containers will fail to bind.
PORTS=(8071 8072 8073 5020 4840 1020 9411)
info "checking host ports ${PORTS[*]}"
BUSY=0
for p in "${PORTS[@]}"; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    warn "port $p is already in use"
    BUSY=1
  fi
done
[ "$BUSY" -eq 0 ] && ok "ports are free" || warn "free the ports above or the range will not bind"

if [ ! -f .env ]; then
  cp .env.example .env
  ok "created .env from .env.example"
else
  info ".env already present, leaving it alone"
fi

info "verifying nothing would bind beyond 127.0.0.1"
if assert_loopback_only -f docker-compose.yml; then
  ok "loopback-only bindings confirmed"
else
  bad "compose config check failed"
  exit 1
fi

info "building images"
dc -f docker-compose.yml build

ok "setup complete"
echo
echo "  next:  ./start.sh          bring the range up (vulnerable defaults)"
echo "         ./status.sh         health + loopback + segmentation audit"
echo "         docs/verification.md   per-scenario test runbook"
