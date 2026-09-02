#!/usr/bin/env bash
# Restore the range to golden state: reload the known-good PLC logic, wipe the
# process simulation back to nominal setpoints, clear historian rows and any
# attacker-planted config. This doubles as the Session 6 "restore from backup"
# incident-response drill.
#   -y   skip the confirmation prompt
set -uo pipefail
cd "$(dirname "$0")"
source ./lib.sh

require_docker

if [ "${1:-}" != "-y" ]; then
  printf '%s' "Restore Cross Creek to golden state (reload PLC logic, reset the process, clear the historian)? [y/N] "
  read -r ans
  case "$ans" in y|Y|yes|YES) ;; *) info "cancelled"; exit 0 ;; esac
fi

FILES=(-f docker-compose.yml)
if dc -f docker-compose.yml -f docker-compose.segmented.yml ps --format '{{.Name}}' 2>/dev/null \
     | grep -q crosscreek-ids; then
  FILES+=(-f docker-compose.segmented.yml)
fi

info "down -v"
dc "${FILES[@]}" down -v

info "rebuild + up"
if ! assert_loopback_only "${FILES[@]}"; then
  bad "loopback guard failed, not restarting"
  exit 1
fi
dc "${FILES[@]}" up -d --build

info "waiting for health (up to 150s)"
deadline=$(( $(date +%s) + 150 ))
while :; do
  unhealthy="$(dc "${FILES[@]}" ps --format '{{.Name}} {{.Health}}' 2>/dev/null \
              | awk '$2 != "healthy" && $2 != "" {print $1}')"
  [ -z "$unhealthy" ] && break
  [ "$(date +%s)" -ge "$deadline" ] && { warn "still not healthy: $unhealthy"; break; }
  sleep 3
done

ok "reset complete, range is back to golden state"
