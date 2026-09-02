# hmi-power: the substation operator screen. Flask serves a single-line
# diagram; the browser polls /api/state, which reads plc-power's DB1 over
# S7comm. Breaker controls POST to /api/cmd, which writes the command byte.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /hmi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8080
CMD ["python", "-u", "app.py"]
