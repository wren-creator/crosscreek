#!/bin/sh
set -e
cd /opt/projects

if [ "${EXPOSE_REMOTE_ACCESS:-1}" = "1" ]; then
  echo "[eng-ws] UNAUTH remote desktop listening on :5900 (weakness on)"
  # stand-in for an exposed, unauthenticated remote-desktop service
  while true; do
    printf 'RFB 003.008\nCross Creek engineering workstation - no authentication configured\n' \
      | nc -l -p 5900 -q 1 >/dev/null 2>&1 || true
  done &
fi

echo "[eng-ws] project share on :8080  (notes.txt has the controller passwords)"
exec python3 -m http.server 8080 --directory /opt/projects
