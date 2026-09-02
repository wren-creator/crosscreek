# process-sim: the physical world. Reads actuator commands from the PLCs over
# their real field protocols, advances a simple lumped model of the plant and
# the substation, writes the resulting sensor values back. Arithmetic, not
# computational fluid dynamics: open a valve and the chlorine rises.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /sim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8099
CMD ["python", "-u", "sim.py"]
