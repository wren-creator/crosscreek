# router-fw: the Purdue-model boundary between edge, enterprise, DMZ and the
# two OT segments. nftables. FW_MODE=1 forwards everything (flat, the default
# for the attack half); FW_MODE=0 enforces zones and conduits.
#
# The image also carries sshd so docker-compose.segmented.yml can reuse it as
# the DMZ jump host with a different entrypoint.
FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        nftables iproute2 iputils-ping tcpdump openssh-server ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd

COPY entrypoint.sh /entrypoint.sh
COPY nftables.flat.conf /etc/nftables.flat.conf
COPY nftables.segmented.conf /etc/nftables.segmented.conf
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
