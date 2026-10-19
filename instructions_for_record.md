I checked your machine and didn't change anything. Here's what I found:

- Docker Desktop is now 4.94.0. The CVE-2025-9074 hole we found on 4.43.1 was fixed in 4.44.3, so your Mac is no longer exposed. The plan stays the same, though: malware runs happen inside the VM, not Docker Desktop.
- Your Lima VM dvg-lab is running. It has Ubuntu 24.04, 4 CPUs, 6 GiB of memory, and mounts: null, so it can't see any of your Mac folders. That's the setup we want.
- The VM has no Docker yet. That's the main thing still to do.
- The MalSkillBench runner breaks two of our safety rules. Core/verification/sandbox.py:229 runs containers with --network host, which gives them the VM's internet. Line 232 also passes your API key into the container. Step 7 fixes both.

Phases A to F are in the VM; type the commands yourself. Phase G is my code patch.

---

A. Copy the code into the VM (run on your Mac)

There are no shared folders, so we copy a tarball. We leave out Logs/, which is about 750 MB, and llm_config.json, which has your keys.
cd ~/Desktop/Projects/School/Divergence/vendor
tar --exclude='MalSkillBench/Logs' --exclude='MalSkillBench/Configs/llm_config.json' \
    -czf /tmp/msb.tgz MalSkillBench
limactl copy /tmp/msb.tgz dvg-lab:/home/$USER.linux/
rm /tmp/msb.tgz
If the copy complains about the path, use limactl copy /tmp/msb.tgz dvg-lab:~/msb.tgz instead.

B. Install Docker Engine inside the VM

limactl shell dvg-lab
Then, inside the VM:
sudo apt-get update && sudo apt-get install -y ca-certificates curl git python3-venv
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
sudo usermod -aG docker $USER
exit
Re-enter so the group change applies, then test:
limactl shell dvg-lab
docker run --rm hello-world
Don't forward the VM's Docker socket to your Mac, even though Lima's docker template does this. Keeping that socket inside the VM is what makes it a boundary.

C. Unpack and build the sandbox image (in the VM)

mkdir -p ~/dvg && tar -xzf ~/msb.tgz -C ~/dvg && rm ~/msb.tgz
cd ~/dvg/MalSkillBench
docker build -t malskillbench/verification-sandbox:latest Core/verification/docker
docker run --rm --entrypoint opencode malskillbench/verification-sandbox:latest --version
Write the OpenCode version into sandbox/setup_notes.md. The Dockerfile doesn't pin it, and you need it for the report.

D. Create the sealed network (in the VM)

docker network create --internal --subnet 172.30.0.0/24 dvg-isolated
--internal means containers on this network have no route out: no internet, and no access to the VM or your Mac.

E. Set up a fake internet with INetSim (in the VM)

INetSim answers every DNS, HTTP and other request with fake responses. This lets multi-stage malware keep running so you can see what it does, without it ever reaching a real server.
mkdir -p ~/dvg/inetsim && cd ~/dvg/inetsim
cat > Dockerfile <<'EOF'
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends inetsim && rm -rf /var/lib/apt/lists/*
RUN sed -i -e 's/^#\?service_bind_address.*/service_bind_address 0.0.0.0/' \
           -e 's/^#\?dns_default_ip.*/dns_default_ip 172.30.0.2/' /etc/inetsim/inetsim.conf
CMD ["inetsim", "--bind-address=0.0.0.0"]
EOF
docker build -t dvg/inetsim .
docker run -d --name inetsim --restart unless-stopped --network dvg-isolated --ip 172.30.0.2 dvg/inetsim
docker logs inetsim | tail

F. Set up the LLM proxy that holds the key (in the VM)

This proxy is the only thing that can reach the real internet. It sits on both networks, forwards only /api/v1/ to OpenRouter, and adds the key itself, so the malware container never sees it.
mkdir -p ~/dvg/llm-proxy && cd ~/dvg/llm-proxy
cat > default.conf.template <<'EOF'
server {
  listen 8080;
  location /api/v1/ {
    proxy_pass https://openrouter.ai/api/v1/;
    proxy_ssl_server_name on;
    proxy_set_header Host openrouter.ai;
    proxy_set_header Authorization "Bearer ${OPENROUTER_API_KEY}";
  }
  location / { return 403; }
}
EOF
read -s OPENROUTER_API_KEY && export OPENROUTER_API_KEY   # paste the key; nothing shows and it stays out of shell history
docker run -d --name llm-proxy --restart unless-stopped -e OPENROUTER_API_KEY \
  -v ~/dvg/llm-proxy/default.conf.template:/etc/nginx/templates/default.conf.template:ro \
  nginx:1.27-alpine
docker network connect --ip 172.30.0.3 dvg-isolated llm-proxy
unset OPENROUTER_API_KEY
In OpenRouter, give this key a low credit limit. A malicious skill can't steal the key, but it can still spend credit through the proxy.

Check the isolation (all four must behave as described):
# 1. Real internet is unreachable → should fail or time out
docker run --rm --network dvg-isolated curlimages/curl -s -m 5 http://1.1.1.1; echo "exit=$?"
# 2. Any domain resolves to INetSim → should return INetSim's fake page
docker run --rm --network dvg-isolated --dns 172.30.0.2 curlimages/curl -s -m 5 http://evil-c2.example
# 3. The proxy adds the key → should return JSON about your key, not a 401 error
docker run --rm --network dvg-isolated curlimages/curl -s http://llm-proxy:8080/api/v1/key
# 4. Every other path is blocked → should return 403
docker run --rm --network dvg-isolated curlimages/curl -s -o /dev/null -w '%{http_code}\n' http://llm-proxy:8080/

G. Patch the runner (my part, once you say go)

sandbox.py needs these changes before any malicious skill runs:
- Network: replace --network host with --network dvg-isolated --dns 172.30.0.2.
- Hardening flags: add --cap-drop ALL --cap-add SYS_PTRACE --security-opt no-new-privileges --pids-limit 256. SYS_PTRACE stays because strace needs it.
- Key and endpoint: in llm_config.json, set query_type: "custom", api_base: "http://llm-proxy:8080/api/v1", a dummy api_key, and the OpenRouter model ID you choose. The runner already turns that into the OpenCode provider config.
- Read-only filesystem: add --read-only only after the first run works, because OpenCode writes to its home directory.

After the patch, copy the updated runner into the VM. Run vendor/smoke_test.py there on the benign 12306 skill first, then one malicious skill. Then copy the evidence back with limactl copy -r dvg-lab:<path> data/supplementary/.

AGT (pip install "agent-governance-toolkit[full]==<exact version>") comes later, once your Phase 1 experiments are giving results you trust. That's the rule in your setup notes.

Run A to F, paste me the output of the four checks, and tell me whether to make the Phase G patch.