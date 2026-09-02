# attacker: the analyst workstation. Generic tooling only, nmap plus the same
# open-source protocol libraries a real assessor would reach for. No packaged
# point-and-click weapon; the scripts under /opt/scripts are hardcoded to lab
# addresses. The box sits on an internal-only bridge and has no route off the
# lab except the static one this image adds to reach the range through the
# firewall.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap tcpdump iproute2 iputils-ping netcat-openbsd curl less vim-tiny \
        dnsutils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        pymodbus==3.6.9 python-snap7==2.0.2 cpppo==5.2.2 requests==2.32.3

COPY scripts/ /opt/scripts/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /opt/scripts/*.py 2>/dev/null || true

ENTRYPOINT ["/entrypoint.sh"]
