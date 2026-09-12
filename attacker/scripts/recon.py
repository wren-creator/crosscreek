#!/usr/bin/env python3
"""Scenarios 1-3 and 11, discovery.

  recon.py dns          enumerate the estate from the utility name server
  recon.py sweep        TCP-connect scan the hosts DNS just handed us
  recon.py nmap         full-range nmap scan, then try NSE name/model/version ID
  recon.py registers     walk the coil/register/tag map on each PLC
  recon.py creds        try the factory-default HMI logins
  recon.py engws        pull what the engineering workstation is sharing

Start with `dns`: on the flat range the utility name server answers for the
whole estate and allows a zone transfer, so one query maps every controller by
name. `sweep` then scans what `dns` found instead of walking a raw /24, but
sweep only checks the field protocols' IANA-assigned default ports, and none
of the three PLCs here sits on its default. `nmap` is the real methodology:
scan the whole port range, then try nmap's vendor NSE scripts on whatever
answers, though those scripts key off the default port too and often can't
tell you more than "open". `registers` is the reliable follow-up either way:
once you know the protocol and the real port, talk it directly and walk what
it exposes.
"""
import http.cookiejar
import re
import socket
import subprocess
import sys
import urllib.request

import targets as T

# `nmap` lets its child processes inherit stdout directly (so students see
# nmap's own progress live) while this script's own print() calls go through
# Python's normal buffering. Piped or redirected (not a TTY, e.g. `| head` or
# `docker exec` without `-t`), that buffering can hold our lines back until
# after the subprocess has already written its own output, so the preamble
# looks missing. Force line buffering so ours always lands first.
sys.stdout.reconfigure(line_buffering=True)

# The IANA/vendor defaults. Listed so `sweep` can demonstrate that assuming
# them finds nothing here; none of Cross Creek's PLCs listens on its default,
# see .env.example (PLC_WATER_PORT / PLC_DOSING_PORT / PLC_POWER_PORT).
ICS_PORTS = {502: "Modbus/TCP (default)", 44818: "EtherNet/IP (default)",
             102: "S7comm (default)", 8080: "HTTP (HMI / runtime)",
             22: "ssh", 20000: "DNP3 (default)"}


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
    print(f"[*] TCP-connect sweep of {len(targets)} host(s), IANA default "
          f"ports only")
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
            print(f"    {name:<34} {host:<16} {desc}")
    ports = ",".join(str(p) for p in ICS_PORTS)
    print(f"\n[*] same scan with the real tool:\n"
          f"    nmap -Pn -sT -p {ports} {T.WATER_DOMAIN} {T.POWER_DOMAIN}\n"
          f"    nmap -Pn -sL {T.OT_SUBNET}0/24        # names only, via the resolver")
    print("[*] notice the field protocols (502/102/44818) never show up: "
          "none of Cross Creek's PLCs sits on its default port. an assessor "
          "who stops here reports three dead controllers. run:\n"
          "    python3 recon.py nmap")
    print("[*] the internet should never be able to run this against a real plant")


def nmap_scan():
    """Standard methodology, not the shortcut `sweep` takes: don't assume the
    field-protocol port. Full TCP range first, then point nmap's vendor NSE
    scripts (modbus-discover, s7-info, enip-info) at whatever answers, for
    whatever free device identification they can pull.

    Honest caveat: those three scripts key off the protocol's textbook port
    (or an already-recognised service name), so they may print nothing for a
    port they don't expect, which is exactly this range. When that happens,
    `recon.py registers` (a real protocol client, not a generic scanner) is
    the reliable way to confirm what's actually listening."""
    targets = _targets()
    if not targets:
        print("[!] nothing to scan, try `recon.py dns` first")
        return
    for name, host in sorted(targets.items(), key=lambda kv: kv[1]):
        try:
            host = T.guard(host)
        except SystemExit as exc:
            print(f"[-] {name}: skipped ({exc})")
            continue
        scan_cmd = ["nmap", "-Pn", "-sS", "-p-", "--min-rate", "2000", "-T4", host]
        print(f"\n[*] {name} ({host})")
        print(f"    $ {' '.join(scan_cmd)}")
        try:
            out = subprocess.run(scan_cmd, capture_output=True, text=True,
                                  timeout=120).stdout
        except Exception as exc:
            print(f"    [-] {exc}")
            continue
        ports = re.findall(r"^(\d+)/tcp\s+open", out, re.M)
        if not ports:
            print("    no open TCP ports")
            continue
        print(f"    open: {', '.join(ports)}")
        id_cmd = ["nmap", "-Pn", "-sV", "--version-intensity", "0",
                  "--script-timeout", "20s", "--host-timeout", "60s",
                  "--script", "modbus-discover,s7-info,enip-info",
                  "-p", ",".join(ports), host]
        print(f"    $ {' '.join(id_cmd)}")
        try:
            subprocess.run(id_cmd, timeout=90)
        except subprocess.TimeoutExpired:
            print("    [-] identification timed out, moving on")
    print("\n[*] the NSE scripts above only fire on a protocol's default "
          "port (or a service name nmap already recognised); a blank result "
          "or 'unknown' service just means this port isn't it. Confirm what "
          "you actually found with the real protocol: python3 recon.py registers")


def registers():
    """Once nmap has told you the protocol and the real port, walk what it
    exposes. Modbus and S7 addressing is raw and numeric, so this is a
    genuine blind walk, the protocol carries no data dictionary. EtherNet/IP
    tags are named, so a real assessment gets the names from an engineering
    file (scenario 3) or a Logix-class controller's tag-directory service;
    this cpppo target doesn't run that service, so the names below are the
    ones the golden program uses, not something the wire handed us for free.
    """
    print(f"[*] plc-water   Modbus/TCP   {T.PLC_WATER}:{T.MODBUS_PORT}")
    try:
        from pymodbus.client import ModbusTcpClient
        c = ModbusTcpClient(T.guard(T.PLC_WATER), port=T.MODBUS_PORT, timeout=3)
        c.connect()
        di = c.read_discrete_inputs(0, 16, slave=1)
        co = c.read_coils(0, 24, slave=1)
        hr = c.read_holding_registers(0, 24, slave=1)
        ir = c.read_input_registers(0, 16, slave=1)
        print(f"    discrete inputs 0-15 : {list(map(int, di.bits[:16]))}")
        print(f"    coils           0-23 : {list(map(int, co.bits[:24]))}")
        print(f"    holding regs    0-23 : {hr.registers}")
        print(f"    input regs      0-15 : {ir.registers}")
        c.close()
    except Exception as exc:
        print(f"    [-] {exc}")

    print(f"\n[*] plc-power   S7comm      {T.PLC_POWER}:{T.S7_PORT}")
    try:
        import snap7
        c = snap7.client.Client()
        c.connect(socket.gethostbyname(T.guard(T.PLC_POWER)), 0, 1, T.S7_PORT)
        db = c.db_read(1, 0, 24)
        print(f"    DB1 bytes 0-23 (hex) : {bytes(db).hex(' ')}")
        c.disconnect()
    except Exception as exc:
        print(f"    [-] {exc}")

    print(f"\n[*] plc-dosing  EtherNet/IP {T.PLC_DOSING}:{T.ENIP_PORT}")
    try:
        from cpppo.server.enip import client as enip_client
        ip = socket.gethostbyname(T.guard(T.PLC_DOSING))
        tags = ["DoseSetpoint", "DoseRate", "FlowFeedback",
                 "Mode", "LogicRev", "LogicForced"]
        with enip_client.connector(host=ip, port=T.ENIP_PORT, timeout=3) as conn:
            results = conn.pipeline(
                operations=enip_client.parse_operations(tags), depth=1)
            for tag, (_, _, _, _, sts, val) in zip(tags, results):
                print(f"    {tag:<14} = {val}  (sts {sts})")
        print("    tag names came from the golden program, not the wire, "
              "see the docstring above")
    except Exception as exc:
        print(f"    [-] {exc}")


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
    {"dns": dns, "sweep": sweep, "nmap": nmap_scan, "registers": registers,
     "creds": creds, "engws": engws}.get(
        sys.argv[1] if len(sys.argv) > 1 else "dns",
        lambda: print(__doc__),
    )()
