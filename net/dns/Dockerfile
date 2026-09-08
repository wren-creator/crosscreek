# dns: the utility's authoritative name server. A real small utility runs one
# of these for its public web/VPN presence and, more often than anyone admits,
# lets it answer for the internal estate too. CoreDNS, authoritative-only, no
# recursion and no upstream: the box is offline like the rest of the range.
#
# Flat build (DNS_AXFR_OPEN=1): full forward zones for every asset plus a
# reverse zone, and zone transfer (AXFR) open to the world. One `dig axfr` from
# the edge and you have the whole plant. Segmented build: split-horizon public
# view only (ns1/www/vpn), AXFR refused.
FROM alpine:3.20

RUN apk add --no-cache coredns

COPY Corefile.flat Corefile.segmented /etc/coredns/
COPY zones/ /etc/coredns/zones/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 53/udp 53/tcp
ENTRYPOINT ["/entrypoint.sh"]
