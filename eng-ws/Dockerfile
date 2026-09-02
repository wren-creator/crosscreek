# eng-ws: the engineering workstation. It holds the PLC project files and a
# notes file with controller addresses and passwords, and (when
# EXPOSE_REMOTE_ACCESS=1) answers an unauthenticated remote-desktop port. It is
# the pivot box for scenarios 2 and 3.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY project-files/ /opt/projects/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && cp /opt/projects/notes.txt /opt/projects/README.txt

EXPOSE 8080 5900
ENTRYPOINT ["/entrypoint.sh"]
