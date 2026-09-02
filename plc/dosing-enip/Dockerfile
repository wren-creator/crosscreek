# plc-dosing: the chlorine dosing controller. An Allen-Bradley-style device that
# speaks EtherNet/IP (CIP) on :44818, served by an embedded cpppo simulator.
# Tags: DoseSetpoint, DoseRate, FlowFeedback, Mode, LogicRev, LogicForced.
#
# ENIP_ALLOW_LOGIC_DOWNLOAD=1 leaves the controller in REMOTE and runs an
# unauthenticated "logic update" service on :8080 that a client can POST to in
# order to push a program that forces the metering pump wide open, defeating
# the downstream overdose interlock. That is scenario 8, and it is a documented
# stand-in for a real Studio 5000 download, not the exact wire format.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /plc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 44818 8080
CMD ["python", "-u", "plc.py"]
