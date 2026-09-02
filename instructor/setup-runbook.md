# Cross Creek 101 — setup runbook

## Before the class

1. On a machine that matches the student environment, `git clone` the repo and run:
   ```bash
   ./setup.sh            # builds all ten images (5–10 min the first time)
   ./start.sh
   ./status.sh           # must end "audit clean"
   ./start.sh --segmented
   ./status.sh
   ./stop.sh
   ```
2. Build the offline fallback in case classroom wifi is bad or absent:
   ```bash
   docker save $(docker images --format '{{.Repository}}:{{.Tag}}' | grep '^crosscreek-') \
     -o crosscreek-images.tar
   ```
   Students load it with `docker load -i crosscreek-images.tar` and then
   `./start.sh` skips the build.
3. Print `scenarios-trainee.md` and `rubric.md`. Keep `scenarios.md` and
   `ctf/answers.txt` to yourself.

## Host requirements

- Docker Engine 24+ or Docker Desktop, `docker compose` v2
- ~8 GB RAM free, ~6 GB disk for the images
- Ports free on `127.0.0.1`: 8071, 8072, 8073, 5020, 4840, 1020, 9411
  (`setup.sh` checks and warns)
- Linux, macOS, or Windows/WSL2. On Apple Silicon everything runs native arm64.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `setup.sh` warns a port is in use | another service on 8071–9411 | stop it, or edit the host-side port in `docker-compose.yml` |
| `plc-power` unhealthy, logs show a snap7 error | slow first start | give it a minute; `docker compose restart plc-power` |
| `process-sim` unhealthy | it starts before the PLCs are ready | it self-heals within ~15 s; check again |
| attacker can't reach OT in flat mode | stale networks from a previous run | `./stop.sh --all` then `./setup.sh && ./start.sh` |
| `ids` unhealthy in segmented mode | Suricata still loading rules | wait ~20 s; check `docker logs crosscreek-ids` |
| HMI shows "plc unreachable" | PLC container restarted, HMI kept a dead socket | reload the page; the client reconnects |
| nothing on `:9411` | you are in flat mode; the IDS only runs segmented | `./start.sh --segmented` |

## Between cohorts

```bash
./reset.sh -y          # golden PLC logic, nominal setpoints, cleared historian
```

If a student wedged a container badly:

```bash
./stop.sh --all        # also drops the volumes
./start.sh
```

## Resetting mid-session

`./reset.sh` is safe to run any time and is itself a teaching moment in
Session 6 (it is the recovery drill). It takes about a minute.
