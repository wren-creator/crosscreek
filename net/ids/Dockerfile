# ids: Suricata watching every segment the boundary firewall bridges (it shares
# router-fw's network namespace). Custom rules flag unauthorised reach-attempts
# and write commands to the ICS protocols. A tiny HTTP server on :9411 tails the
# EVE json so students can watch alerts land.
#
# suricata was dropped from Debian 12, so this uses the maintained community
# image (Suricata 8, AlmaLinux, ships python3).
FROM jasonish/suricata:8.0

RUN (command -v microdnf && microdnf install -y iproute) \
    || (command -v dnf && dnf install -y iproute) || true

COPY rules/crosscreek.rules /etc/suricata/rules/crosscreek.rules
COPY entrypoint.sh /usr/local/bin/cc-entrypoint.sh
COPY evetail.py /opt/evetail.py
RUN chmod +x /usr/local/bin/cc-entrypoint.sh

EXPOSE 9411
ENTRYPOINT ["/usr/local/bin/cc-entrypoint.sh"]
