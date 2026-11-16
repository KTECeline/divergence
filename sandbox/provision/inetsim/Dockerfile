# Fake internet (setup_notes.md Step E). Answers HTTP, HTTPS, SMTP, FTP, IRC and
# other protocols with fake but valid responses, so a multi-stage attack keeps
# going and shows its behaviour in the trace without reaching a real host.
# INetSim's own DNS service does not start on Ubuntu 24.04 (Problem 2 in the
# notes); DNS is served by the separate fakedns container instead.
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends inetsim && rm -rf /var/lib/apt/lists/*
RUN sed -i -e 's/^#\?service_bind_address.*/service_bind_address 0.0.0.0/' \
           -e 's/^#\?dns_default_ip.*/dns_default_ip 172.30.0.2/' /etc/inetsim/inetsim.conf
CMD ["inetsim", "--bind-address=0.0.0.0"]
