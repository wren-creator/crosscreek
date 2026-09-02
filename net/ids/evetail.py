#!/usr/bin/env python3
"""Serve the last N Suricata alerts as text on :9411, so students can watch
them land without learning a SIEM first."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

EVE = "/var/log/suricata/eve.json"


def alerts(limit=80):
    out = []
    if not os.path.exists(EVE):
        return ["(no eve.json yet)"]
    with open(EVE) as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("event_type") != "alert":
                continue
            a = ev["alert"]
            out.append(
                f"{ev.get('timestamp','')[:19]}  {ev.get('src_ip')}:"
                f"{ev.get('src_port')} -> {ev.get('dest_ip')}:{ev.get('dest_port')}"
                f"  [{a.get('signature')}]"
            )
    return out[-limit:] or ["(no alerts yet)"]


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("Cross Creek IDS - recent alerts\n"
                + "=" * 60 + "\n" + "\n".join(alerts()) + "\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9411), H).serve_forever()
