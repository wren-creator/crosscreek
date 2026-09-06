#!/usr/bin/env bash
# Bring the range up. Refuses to launch if any published port would bind
# beyond 127.0.0.1.
#   --segmented   start with the defended topology (segmentation, allowlists,
#                 IDS on, controller hardening) instead of the flat default
#   --build       rebuild images before starting, so local edits to the HMIs
#                 or other services are picked up without a full ./reset.sh
set -uo pipefail
cd "$(dirname "$0")"
source ./lib.sh

COMPOSE_ARGS=(-f docker-compose.yml)
MODE="flat (vulnerable defaults)"
UP_ARGS=(-d)
for arg in "$@"; do
  case "$arg" in
    --segmented)
      COMPOSE_ARGS+=(-f docker-compose.segmented.yml)
      MODE="segmented (defended)"
      info "segmented topology selected"
      ;;
    --build)
      UP_ARGS+=(--build)
      info "rebuilding images before start"
      ;;
    *)
      bad "unknown option: $arg  (expected --segmented and/or --build)"
      exit 1
      ;;
  esac
done

require_docker

info "loopback-only guard"
if ! assert_loopback_only "${COMPOSE_ARGS[@]}"; then
  bad "not starting"
  exit 1
fi
ok "all published ports bind to 127.0.0.1"

info "starting containers"
dc "${COMPOSE_ARGS[@]}" up "${UP_ARGS[@]}"

info "waiting for health (up to 150s)"
deadline=$(( $(date +%s) + 150 ))
while :; do
  unhealthy="$(dc "${COMPOSE_ARGS[@]}" ps --format '{{.Name}} {{.Health}}' 2>/dev/null \
              | awk '$2 != "healthy" && $2 != "" {print $1}')"
  [ -z "$unhealthy" ] && break
  if [ "$(date +%s)" -ge "$deadline" ]; then
    warn "still not healthy: $unhealthy"
    warn "check: ./status.sh  and  docker compose logs"
    break
  fi
  sleep 3
done

echo
ok "Cross Creek is up  [$MODE]"
echo "  water HMI      http://127.0.0.1:8071/"
echo "  power HMI      http://127.0.0.1:8072/"
echo "  water PLC      127.0.0.1:5020   Modbus/TCP"
echo "  dosing PLC     127.0.0.1:4840   EtherNet/IP (CIP)"
echo "  substation RTU 127.0.0.1:1020   S7comm"
echo "  IDS events     127.0.0.1:9411/  (segmented mode only)"
echo
echo "  attacker shell:        docker exec -it crosscreek-attacker bash"
echo "  instructor answer key: docs/scenarios.md"
echo "  reset to golden state: ./reset.sh"
echo "  defended run:          ./start.sh --segmented"
echo "  rebuild then start:    ./start.sh --build"
