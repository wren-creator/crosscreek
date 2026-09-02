# plc-water: the water plant controller.
#
# A soft PLC that speaks real Modbus/TCP. It runs an OpenPLC-style scan loop
# over a swappable control program written in Structured Text-flavoured Python.
# The web UI on :8080 mirrors the OpenPLC runtime: view the running program,
# stop/start the CPU, and (when the keyswitch allows it) upload a new program.
# That upload path is scenario 9. It is a stand-in for a vendor download, and
# the docs say so.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /plc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /plc/logic/runtime && cp /plc/logic/golden_water.py /plc/logic/runtime/active.py

EXPOSE 502 8080
CMD ["python", "-u", "plc.py"]
