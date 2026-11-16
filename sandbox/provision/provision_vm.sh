#!/usr/bin/env bash
# Build the Divergence sandbox INSIDE the Linux VM. This is sandbox/setup_notes.md
# Steps B-H as one repeatable script. It is not run by hand: sandbox/setup_sandbox.sh
# (on the host) copies the repo's sandbox files to ~/dvg-setup and calls it.
#
#   provision_vm.sh system               Step B: Docker Engine + base tools (uses sudo)
#   provision_vm.sh build [--key-stdin] [--rekey]
#                                        Steps C-H: pinned MalSkillBench runner + patch,
#                                        sandbox images, sealed network, fake internet,
#                                        fake DNS, LLM proxy, runners, Python env, configs
#   provision_vm.sh check                the isolation checks from the notes
#
# Safe to re-run: every step is skipped when its result already exists.
# --key-stdin reads the OpenRouter API key as the first line of stdin, so the key
# is never on a command line. It ends up only inside the llm-proxy container.
# --rekey replaces the llm-proxy container with one holding a new key.
#
# Optional overrides (environment):
#   DVG_OPENCODE_VERSION   agent CLI version in the sandbox image (default 1.19.3,
#                          the version the dataset was captured with; "latest" = unpinned)
#   DVG_AGENT_MODEL        model for the aligned-agent mode   (Configs/llm_config.json)
#   DVG_INSTRUCTED_MODEL   model for the instructed mode      (Configs/llm_config_instructed.json)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # ~/dvg-setup (holds sandbox/ and vendor/)
DVG="$HOME/dvg"
MSB="$DVG/MalSkillBench"
MSB_REPO="https://github.com/lxyeternal/MalSkillBench.git"
MSB_COMMIT="06e083125d5ec5dd7a189dfedadfe587a70635b9"      # the commit the patch was made against
OPENCODE_VERSION="${DVG_OPENCODE_VERSION:-1.19.3}"
NET="dvg-isolated"
SUBNET="172.30.0.0/24"
IP_INETSIM="172.30.0.2"
IP_PROXY="172.30.0.3"
IP_DNS="172.30.0.4"
BASE_IMAGE="malskillbench/verification-sandbox:latest"
SYNTH_IMAGE="dvg/sandbox-synthetic:latest"
CURL_IMAGE="curlimages/curl:latest"

step() { printf '\n== %s\n' "$*"; }
info() { printf '   %s\n' "$*"; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

have_image()     { docker image inspect "$1" >/dev/null 2>&1; }
have_container() { docker container inspect "$1" >/dev/null 2>&1; }
ensure_running() { [ "$(docker container inspect -f '{{.State.Running}}' "$1")" = "true" ] || docker start "$1" >/dev/null; }

apt_update() {  # the Ubuntu mirrors sometimes answer 403 for a moment on a fresh VM: retry
  local n
  for n in 1 2 3 4 5; do
    sudo apt-get update -qq && return 0
    info "apt-get update failed (attempt $n of 5); retrying in 15 s"
    sleep 15
  done
  die "apt-get update keeps failing: check the VM's internet access and re-run"
}

require_vm() {
  [ "$(uname -s)" = "Linux" ] || die "this script runs inside the Linux VM, not on the host"
  # A host folder mounted into the VM would let a skill that escapes its container
  # read or change host files. The sandbox is only built in a VM without one.
  local shared
  shared="$(findmnt -n -o TARGET,FSTYPE -t virtiofs,9p,fuse.sshfs 2>/dev/null || true)"
  if [ -n "$shared" ] && [ "${DVG_ALLOW_MOUNTS:-0}" != "1" ]; then
    die "this VM has host folders mounted:
$shared
Untrusted skills must run in a VM with no shared folders. Create the VM from
sandbox/lima/dvg-lab.yaml (it sets 'mounts: []')."
  fi
}

# ---------------------------------------------------------------- system (Step B)
phase_system() {
  require_vm
  if command -v docker >/dev/null 2>&1 && id -nG "$USER" | tr ' ' '\n' | grep -qx docker \
     && command -v git >/dev/null 2>&1 && python3 -m venv --help >/dev/null 2>&1; then
    step "Docker Engine and base tools already installed"
    return
  fi
  step "Installing base tools and Docker Engine (Docker's apt repository)"
  export DEBIAN_FRONTEND=noninteractive
  apt_update
  sudo apt-get install -y -qq ca-certificates curl git python3-venv
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  apt_update
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin
  # Group membership only applies to new logins; setup_sandbox.sh restarts the VM if needed.
  sudo usermod -aG docker "$USER"
  info "installed: $(docker --version)"
}

# ---------------------------------------------------------------- build (Steps C-H)
write_llm_config() {  # <file> <model>: points OpenCode at the proxy; holds no secret
  cat > "$1" <<EOF
{ "query_type": "custom",
  "llm_providers": { "custom": {
      "api_key": "injected-by-proxy",
      "api_base": "http://llm-proxy:8080/api/v1",
      "model": "$2" } } }
EOF
}

phase_build() {
  local key="" key_stdin=0 rekey=0
  for a in "$@"; do
    case "$a" in
      --key-stdin) key_stdin=1 ;;
      --rekey)     rekey=1 ;;
      *) die "unknown option: $a" ;;
    esac
  done
  # Read the key before anything else can consume stdin.
  if [ "$key_stdin" = 1 ]; then IFS= read -r key || true; fi
  exec </dev/null

  require_vm
  docker info >/dev/null 2>&1 || die "docker is not usable by $USER yet (run the 'system' phase, then restart the VM)"
  mkdir -p "$DVG"

  # -- Step C: the MalSkillBench runner, pinned + patched (code only, no dataset)
  if [ -f "$MSB/Core/verification/sandbox.py" ]; then
    step "MalSkillBench runner already present"
    grep -q DVG_DIRECT_ENTRYPOINT "$MSB/Core/verification/sandbox.py" \
      || die "$MSB exists but is not patched (no DVG_DIRECT_ENTRYPOINT hook). Move it away and re-run."
  else
    step "Fetching the MalSkillBench runner at ${MSB_COMMIT:0:10} and applying the Divergence patch"
    local tmp
    tmp="$(mktemp -d "$DVG/msb.XXXXXX")"
    git -C "$tmp" init -q
    git -C "$tmp" remote add origin "$MSB_REPO"
    git -C "$tmp" sparse-checkout set Core Utils Configs      # the runner only; the dataset is not needed
    git -C "$tmp" fetch -q --depth 1 --filter=blob:none origin "$MSB_COMMIT"
    git -C "$tmp" checkout -q FETCH_HEAD
    git -C "$tmp" apply "$SRC/sandbox/malskillbench_patches.diff"
    rm -rf "$tmp/.git"
    chmod 755 "$tmp"
    mv "$tmp" "$MSB"
    info "patched runner sha256: $(sha256sum "$MSB/Core/verification/sandbox.py" | cut -c1-16)..."
  fi
  # Skills under review are unpacked to Dataset/Skills/candidate/<folder> by the trial runner.
  mkdir -p "$MSB/Logs" "$MSB/Dataset/Skills/candidate" "$MSB/Dataset/Skills/malware"
  # vendor/pilot_run.py reads this inventory at import; without the dataset it is empty.
  [ -f "$MSB/Dataset/Skills/malware/_source_inventory.txt" ] || : > "$MSB/Dataset/Skills/malware/_source_inventory.txt"

  # -- Step C: the sandbox image every skill runs in
  if have_image "$BASE_IMAGE"; then
    step "Sandbox image already built ($BASE_IMAGE)"
  else
    step "Building the sandbox image ($BASE_IMAGE, OpenCode $OPENCODE_VERSION)"
    if [ "$OPENCODE_VERSION" != "latest" ]; then
      # Upstream installs opencode-ai unpinned; pin it so a rebuild matches the dataset's agent CLI.
      sed -i "s/npm install -g opencode-ai\$/npm install -g opencode-ai@$OPENCODE_VERSION/" \
        "$MSB/Core/verification/docker/Dockerfile"
    fi
    docker build -q -t "$BASE_IMAGE" "$MSB/Core/verification/docker" >/dev/null
  fi
  info "OpenCode in image: $(docker run --rm --entrypoint opencode "$BASE_IMAGE" --version 2>/dev/null || echo unknown)"

  # -- runners and the synthetic-user image (Stage 3)
  step "Installing the Divergence runners into $DVG"
  for d in direct_exec instructed_agent synthetic_user; do
    mkdir -p "$DVG/$d"
    cp -R "$SRC/sandbox/$d/." "$DVG/$d/"
  done
  cp "$SRC/vendor/batch_run.py" "$SRC/vendor/pilot_run.py" "$DVG/"
  cp "$SRC/sandbox/demo_trial.sh" "$DVG/demo_trial.sh"
  chmod +x "$DVG/direct_exec/entrypoint_direct.sh"
  [ -f "$DVG/synthetic_user/workspace/project/.env" ] \
    || info "note: synthetic_user/workspace/project/.env is missing from this checkout (fake keys a payload may look for)"

  if have_image "$SYNTH_IMAGE"; then
    step "Synthetic-user image already built ($SYNTH_IMAGE)"
  else
    step "Building the synthetic-user image ($SYNTH_IMAGE)"
    docker build -q -t "$SYNTH_IMAGE" "$DVG/synthetic_user" >/dev/null
  fi

  # -- Step D: the sealed network
  if docker network inspect "$NET" >/dev/null 2>&1; then
    step "Sealed network already exists ($NET)"
  else
    step "Creating the sealed network ($NET, --internal, $SUBNET)"
    docker network create --internal --subnet "$SUBNET" "$NET" >/dev/null
  fi
  [ "$(docker network inspect -f '{{.Internal}}' "$NET")" = "true" ] \
    || die "network $NET exists but is not --internal: skills on it could reach the internet"

  # -- Steps E / E2: fake internet + fake DNS
  if have_container inetsim; then
    step "Fake internet already running (inetsim)"; ensure_running inetsim
  else
    step "Starting the fake internet (inetsim at $IP_INETSIM)"
    mkdir -p "$DVG/inetsim" && cp "$SRC/sandbox/provision/inetsim/Dockerfile" "$DVG/inetsim/"
    docker build -q -t dvg/inetsim "$DVG/inetsim" >/dev/null
    docker run -d --name inetsim --restart unless-stopped --network "$NET" --ip "$IP_INETSIM" dvg/inetsim >/dev/null
  fi
  if have_container fakedns; then
    step "Fake DNS already running (fakedns)"; ensure_running fakedns
  else
    step "Starting the fake DNS (fakedns at $IP_DNS)"
    mkdir -p "$DVG/fakedns" && cp "$SRC/sandbox/provision/fakedns/Dockerfile" "$DVG/fakedns/"
    docker build -q -t dvg/fakedns "$DVG/fakedns" >/dev/null
    docker run -d --name fakedns --restart unless-stopped --network "$NET" --ip "$IP_DNS" dvg/fakedns >/dev/null
  fi

  # -- Step F: the LLM proxy, the only holder of the API key
  if have_container llm-proxy && [ "$rekey" = 0 ]; then
    step "LLM proxy already running (llm-proxy); use --rekey to change its key"; ensure_running llm-proxy
  else
    [ -n "$key" ] || die "no OpenRouter API key was given, and the llm-proxy container does not exist yet"
    step "Starting the LLM proxy (llm-proxy at $IP_PROXY)"
    docker rm -f llm-proxy >/dev/null 2>&1 || true
    mkdir -p "$DVG/llm-proxy" && cp "$SRC/sandbox/provision/llm-proxy/default.conf.template" "$DVG/llm-proxy/"
    # The key travels in the docker client's environment (-e NAME, no value), never in argv.
    OPENROUTER_API_KEY="$key" docker run -d --name llm-proxy --restart unless-stopped -e OPENROUTER_API_KEY \
      -v "$DVG/llm-proxy/default.conf.template:/etc/nginx/templates/default.conf.template:ro" \
      nginx:1.27-alpine >/dev/null
    docker network connect --ip "$IP_PROXY" "$NET" llm-proxy
  fi
  key=""

  # -- Step H: Python environment for the runner
  if "$DVG/.venv/bin/python" -c 'import numpy, openai, requests, tenacity, tiktoken' >/dev/null 2>&1; then
    step "Python environment already set up ($DVG/.venv)"
  else
    step "Creating the runner's Python environment ($DVG/.venv)"
    [ -x "$DVG/.venv/bin/python" ] || python3 -m venv "$DVG/.venv"
    if ! "$DVG/.venv/bin/pip" install -q -r "$SRC/sandbox/provision/requirements-vm.txt"; then
      info "pinned versions could not be installed here; installing current versions instead"
      "$DVG/.venv/bin/pip" install -q numpy openai requests tenacity tiktoken
    fi
    "$DVG/.venv/bin/pip" freeze > "$DVG/requirements-vm.txt"
  fi

  # -- model configs (no secret inside: the proxy adds the key)
  step "Writing the model configs"
  local cfg="$MSB/Configs"
  if [ ! -f "$cfg/llm_config.json" ] || [ -n "${DVG_AGENT_MODEL:-}" ]; then
    write_llm_config "$cfg/llm_config.json" "${DVG_AGENT_MODEL:-deepseek/deepseek-v4.1-flash}"
  fi
  if [ ! -f "$cfg/llm_config_instructed.json" ] || [ -n "${DVG_INSTRUCTED_MODEL:-}" ]; then
    write_llm_config "$cfg/llm_config_instructed.json" "${DVG_INSTRUCTED_MODEL:-mistralai/mistral-small-3.2-24b-instruct}"
  fi
  info "aligned-agent model: $(grep -o '"model": *"[^"]*"' "$cfg/llm_config.json" | cut -d'"' -f4)"
  info "instructed model:    $(grep -o '"model": *"[^"]*"' "$cfg/llm_config_instructed.json" | cut -d'"' -f4)"

  phase_check
}

# ---------------------------------------------------------------- check
in_sealed() {  # run curl in a throwaway container on the sealed network, as a skill would be
  docker run --rm --network "$NET" --dns "$IP_DNS" "$CURL_IMAGE" -s -m 8 "$@"
}

phase_check() {
  require_vm
  step "Checking the sandbox"
  local failed=0 code page=""
  ok()  { printf '   PASS  %s\n' "$*"; }
  bad() { printf '   FAIL  %s\n' "$*"; failed=1; }

  # Pull first, so a failed pull is never mistaken for "no route out".
  have_image "$CURL_IMAGE" || docker pull -q "$CURL_IMAGE" >/dev/null || die "could not pull $CURL_IMAGE for the checks"

  for img in "$BASE_IMAGE" "$SYNTH_IMAGE"; do
    if have_image "$img"; then ok "image $img"; else bad "image $img is missing"; fi
  done
  for c in inetsim fakedns llm-proxy; do
    if [ "$(docker container inspect -f '{{.State.Running}}' "$c" 2>/dev/null)" = "true" ]; then ok "container $c is running"
    else bad "container $c is not running"; fi
  done
  if (cd "$MSB" && "$DVG/.venv/bin/python" -c 'from Core.verification.sandbox import DockerSandbox' >/dev/null 2>&1); then
    ok "patched runner imports in the Python environment"
  else bad "the runner does not import (cd $MSB && $DVG/.venv/bin/python -c 'from Core.verification.sandbox import DockerSandbox')"; fi

  # 1. the sealed network must not reach the real internet
  #    (curl exit 7 = could not connect, 28 = timed out; anything else means the check itself did not run)
  local rc=0
  in_sealed -o /dev/null http://1.1.1.1 >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0)    bad "ISOLATION BROKEN: a container on $NET reached the real internet (1.1.1.1). Do not run skills." ;;
    7|28) ok "no route from $NET to the real internet" ;;
    *)    bad "the isolation check could not run (exit $rc)" ;;
  esac

  # 2. any domain lands on the fake internet (INetSim needs a few seconds after first start)
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    page="$(in_sealed http://evil-c2.example/ 2>/dev/null || true)"
    case "$page" in *INetSim*) break ;; esac
    sleep 3
  done
  case "$page" in
    *INetSim*) ok "any domain resolves to the fake internet (INetSim answered evil-c2.example)" ;;
    *) bad "the fake internet did not answer (docker logs inetsim; docker logs fakedns)" ;;
  esac

  # 3. the proxy forwards only the LLM API path
  code="$(in_sealed -o /dev/null -w '%{http_code}' http://llm-proxy:8080/ 2>/dev/null || true)"
  if [ "$code" = "403" ]; then ok "LLM proxy refuses non-API paths (403)"
  else bad "LLM proxy answered '$code' on /, expected 403"; fi

  # 4. the key held by the proxy works (the request below sends no key itself)
  code="$(in_sealed -o /dev/null -w '%{http_code}' http://llm-proxy:8080/api/v1/key 2>/dev/null || true)"
  if [ "$code" = "200" ]; then ok "OpenRouter accepts the key held by the proxy"
  else bad "OpenRouter answered '$code' through the proxy: the key is missing or invalid. Re-run setup_sandbox.sh --rekey"; fi

  if [ "$failed" = 0 ]; then printf '\nSandbox ready.\n'; else printf '\nSandbox NOT ready: fix the FAIL lines above.\n' >&2; exit 1; fi
}

case "${1:-}" in
  system) shift; phase_system "$@" ;;
  build)  shift; phase_build "$@" ;;
  check)  shift; phase_check "$@" ;;
  *) die "usage: provision_vm.sh system | build [--key-stdin] [--rekey] | check" ;;
esac
