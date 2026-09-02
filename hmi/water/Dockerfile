# hmi-water: the water plant operator screen. Flask serves a P&ID; the browser
# polls /api/state, which reads plc-water over Modbus/TCP and returns JSON.
# Operator controls POST to /api/cmd, which writes Modbus coils and registers.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /hmi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8080
CMD ["python", "-u", "app.py"]
