#!/usr/bin/env bash
# One-command setup of the Divergence sandbox: the sealed Linux VM that
# `divergence install --skill-dir <your skill>` runs a skill in before install.
#
# Run on the host (macOS or Linux). After `pip install divergence-agt` (the package
# bundles this script and the files it copies), or from a clone of the repo:
#
#   divergence setup-sandbox                   # create the VM "dvg-lab" and build everything
#   divergence setup-sandbox --check           # re-run the isolation checks only
#   divergence setup-sandbox --rekey           # replace the OpenRouter key held by the proxy
#   divergence setup-sandbox --vm NAME         # use another VM name
#   (in a clone, `bash sandbox/setup_sandbox.sh ...` does the same)
#
# Needs: Lima 2.x (`brew install lima`), about 30 GiB of disk and 6 GiB of RAM
# for the VM, and an OpenRouter API key (asked for, input hidden; or export
# OPENROUTER_API_KEY first). Give the key a low credit limit: a skill cannot
# read it, but it can spend credit through the proxy.
#
# What it does (the manual version, with the reasons, is sandbox/setup_notes.md):
#   1. creates the VM from sandbox/lima/dvg-lab.yaml (Ubuntu 24.04, no shared folders)
#   2. copies the sandbox files into it (one archive over Lima's SSH; nothing is mounted)
#   3. runs sandbox/provision/provision_vm.sh inside it: Docker Engine, the pinned
#      and patched MalSkillBench runner, the sandbox images, the sealed network,
#      the fake internet + DNS, the LLM proxy, the runners and their Python env
#   4. runs the isolation checks and prints PASS / FAIL for each
#
# Safe to re-run: steps whose result already exists are skipped.
# MalSkillBench (Guo et al., 2026) is fetched from its own repository inside the
# VM; only the runner code is fetched, not the dataset, and nothing of it is
# redistributed here. Its licence (academic research use) applies to your use.
set -euo pipefail

VM="dvg-lab"
REKEY=0
CHECK_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --vm)    VM="${2:?--vm needs a name}"; shift 2 ;;
    --rekey) REKEY=1; shift ;;
    --check) CHECK_ONLY=1; shift ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$HERE")"
# shellcheck disable=SC2016  # $HOME must expand inside the VM, not here
PROVISION='bash "$HOME/dvg-setup/sandbox/provision/provision_vm.sh"'

say() { printf '\n>> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
vm()  { limactl shell --workdir /tmp "$VM" bash -lc "$1"; }

command -v limactl >/dev/null 2>&1 || die "limactl not found. Install Lima first (macOS: brew install lima; https://lima-vm.io)."
[[ "$VM" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "invalid VM name: $VM"

# ---- 1. the VM
status="$(limactl list --format '{{.Status}}' "$VM" 2>/dev/null || true)"
if [ "$CHECK_ONLY" = 1 ]; then
  [ "$status" = "Running" ] || die "VM $VM is ${status:-missing}; run 'divergence setup-sandbox' without --check first"
elif [ -z "$status" ]; then
  say "Creating the VM $VM (downloads Ubuntu 24.04; a few minutes)"
  limactl start --name "$VM" --tty=false "$HERE/lima/dvg-lab.yaml"
elif [ "$status" != "Running" ]; then
  say "Starting the VM $VM"
  limactl start --tty=false "$VM"
else
  say "VM $VM is running"
fi

if [ "$CHECK_ONLY" = 1 ]; then
  vm "$PROVISION check" </dev/null
  exit 0
fi

# ---- 2. copy the sandbox files in (one archive; the VM has no shared folders)
say "Copying the sandbox files into the VM"
for f in sandbox/provision/provision_vm.sh sandbox/malskillbench_patches.diff sandbox/demo_trial.sh \
         sandbox/direct_exec/entrypoint_direct.sh sandbox/instructed_agent/run_instructed.py \
         sandbox/synthetic_user/Dockerfile vendor/batch_run.py vendor/pilot_run.py; do
  [ -f "$REPO/$f" ] || die "missing $f: reinstall divergence-agt, or run this from a full clone of the repository"
done
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
# COPYFILE_DISABLE / --no-xattrs: keep macOS metadata out of the archive
COPYFILE_DISABLE=1 tar --no-xattrs -czf "$tmp/dvg-setup.tgz" -C "$REPO" \
  sandbox/provision sandbox/malskillbench_patches.diff sandbox/demo_trial.sh \
  sandbox/direct_exec sandbox/instructed_agent sandbox/synthetic_user \
  vendor/batch_run.py vendor/pilot_run.py
limactl copy "$tmp/dvg-setup.tgz" "$VM:/tmp/dvg-setup.tgz"
# shellcheck disable=SC2016
vm 'rm -rf "$HOME/dvg-setup" && mkdir -p "$HOME/dvg-setup" && tar -xzf /tmp/dvg-setup.tgz -C "$HOME/dvg-setup" && rm -f /tmp/dvg-setup.tgz' </dev/null

# ---- 3a. Docker Engine and base tools
say "Installing Docker Engine and base tools in the VM"
vm "$PROVISION system" </dev/null
if ! vm 'docker info >/dev/null 2>&1' </dev/null; then
  # The docker group applies to new logins only, and Lima reuses one SSH connection.
  say "Restarting the VM so the docker group applies"
  limactl stop "$VM"
  limactl start --tty=false "$VM"
  vm 'docker info >/dev/null 2>&1' </dev/null || die "docker is still not usable inside $VM (try: limactl shell $VM docker info)"
fi

# ---- 3b. the sandbox itself
# Pass the optional overrides through to the VM (see provision_vm.sh).
envs=""
for v in DVG_OPENCODE_VERSION DVG_AGENT_MODEL DVG_INSTRUCTED_MODEL; do
  if [ -n "${!v:-}" ]; then envs+="$v=$(printf '%q' "${!v}") "; fi
done

need_key=$REKEY
vm 'docker container inspect llm-proxy >/dev/null 2>&1' </dev/null || need_key=1

say "Building the sandbox in the VM (first run: 5 to 15 minutes)"
if [ "$need_key" = 1 ]; then
  key="${OPENROUTER_API_KEY:-}"
  if [ -z "$key" ]; then
    [ -t 0 ] || die "an OpenRouter API key is needed: export OPENROUTER_API_KEY or run this in a terminal"
    printf 'OpenRouter API key for the LLM proxy (input hidden): '
    IFS= read -rs key; printf '\n'
  fi
  [ -n "$key" ] || die "no key entered"
  flags="--key-stdin"; [ "$REKEY" = 1 ] && flags="$flags --rekey"
  # The key goes over stdin (never on a command line) and is stored only inside the proxy container.
  printf '%s\n' "$key" | vm "$envs$PROVISION build $flags"
  key=""
else
  vm "$envs$PROVISION build" </dev/null
fi

cat <<EOF

The sandbox VM "$VM" is ready. Check any skill folder (one that holds a SKILL.md) with:

    divergence install --skill-dir path/to/your-skill$([ "$VM" = dvg-lab ] || printf ' --vm %s' "$VM")

Stop the VM when you are not using it:  limactl stop $VM
Remove it completely:                   limactl delete $VM
EOF
