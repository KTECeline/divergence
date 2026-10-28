# Synthetic-user layer on top of the unchanged sandbox image.
# Every secret is fake and contains the marker DVGCANARY, so a leak is easy to
# spot in strace output and in INetSim's logs. Nothing here is real.
FROM malskillbench/verification-sandbox

# The packages a normal developer's machine would already have. Installing them
# is realistic (a real victim box is not bare) and lets a payload reach its
# malicious step instead of dying on an `import` first, so behaviour is
# observable. These are the most-imported third-party modules across the 573
# script-bearing skills (requests/urllib3 are already in the base image).
RUN pip install --no-cache-dir --break-system-packages \
    pyyaml cryptography psutil python-dotenv gitpython pillow numpy pandas httpx \
    websockets beautifulsoup4 tqdm fernet uv

# Many scripts call `python` (not `python3`); a real dev box has that alias.
RUN ln -sf "$(command -v python3)" /usr/local/bin/python

# jq is used by many skills to parse API responses. It is a single static
# binary (apt is blocked on this host), matched to the image architecture.
# Non-fatal: if the download is blocked, the build still succeeds and those
# skills just hit "jq: not found".
RUN a=$(uname -m); case "$a" in x86_64) j=amd64;; aarch64|arm64) j=arm64;; *) j=amd64;; esac; \
    curl -fsSL -o /usr/local/bin/jq \
      "https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-$j" \
    && chmod +x /usr/local/bin/jq && /usr/local/bin/jq --version || echo "jq download skipped"

COPY home/ /root/
COPY workspace/ /workspace/
RUN chmod 700 /root/.ssh && chmod 600 /root/.ssh/id_ed25519 /root/.aws/credentials /root/.netrc
