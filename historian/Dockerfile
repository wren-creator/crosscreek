# historian: a data historian in the DMZ. Polls the water PLC (Modbus) and the
# substation RTU (S7) and records samples to sqlite. HISTORIAN_READONLY=1 makes
# it refuse to open any write path back into OT (Session 6, one-way link).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8086
CMD ["python", "-u", "historian.py"]
