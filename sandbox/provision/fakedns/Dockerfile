# Fake DNS (setup_notes.md Step E2). Answers every domain with INetSim's IP
# (172.30.0.2) and logs every lookup: `docker logs fakedns` lists the domains a
# skill tried to contact. No upstream resolver, so nothing resolves for real.
FROM alpine:3.20
RUN apk add --no-cache dnsmasq
CMD ["dnsmasq", "--keep-in-foreground", "--no-resolv", "--no-hosts", \
     "--log-queries", "--log-facility=-", "--address=/#/172.30.0.2"]
