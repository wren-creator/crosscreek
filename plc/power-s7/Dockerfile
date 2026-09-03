# plc-power: the substation RTU. A STEMENS-style controller that speaks S7comm
# on :102 via python-snap7's server. It exposes one data block (DB1) holding the
# bus frequency, voltage, load, breaker status and breaker commands. A scan
# loop acts on breaker commands and enforces the operating mode.
#
# S7_NO_PASSWORD=1 lets any client stop the CPU or trip a breaker with no
# authentication (the default weakness). Set to 0 and the scan loop ignores
# unauthenticated trip/stop commands and re-asserts RUN.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /plc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 102 8080
CMD ["python", "-u", "plc.py"]
