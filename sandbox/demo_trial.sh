#!/usr/bin/env bash
# Experiment 7: capture fresh trial runs of ONE skill, in the VM, exactly as the
# dataset was captured: same runners, same sandbox, and the same image per mode
#   direct     -> dvg/sandbox-synthetic (DVGCANARY secrets), only if the skill ships scripts
#   instructed -> default MalSkillBench image, mistral-small-3.2 + compliant trigger
#   agent      -> default image, Stage 2 model (only with --with-agent; costs a little)
# Output: ~/dvg/demo_out/{direct_out,instructed_out,batch_out}/results/<label>/<skill>.json,
# the same layout as data/raw/traces/, then packed to /tmp/demo_out.tgz.
#
# In the VM:
#   source ~/dvg/.venv/bin/activate && cd ~/dvg/MalSkillBench
#   bash ~/dvg/demo_trial.sh malware/<skill-folder> [--with-agent]
# Then on the Mac:
#   limactl copy dvg-lab:/tmp/demo_out.tgz /tmp/ && mkdir -p data/raw/traces/demo \
#     && tar -xzf /tmp/demo_out.tgz -C data/raw/traces/demo
#   .venv/bin/python sandbox/demo_pipeline.py --traces-root data/raw/traces/demo --skill malware/<skill-folder>
set -euo pipefail

ID="${1:?usage: demo_trial.sh <label>/<skill-folder> [--with-agent]}"
WITH_AGENT="${2:-}"
DVG=~/dvg
MSB="$DVG/MalSkillBench"
export DVG_MSB_ROOT="$MSB"   # the runners default to the Mac layout (vendor/MalSkillBench)
OUT="$DVG/demo_out"
SKILL_DIR="$MSB/Dataset/Skills/$ID"
[ -d "$SKILL_DIR" ] || { echo "no such skill: $SKILL_DIR"; exit 1; }

IDS=$(mktemp); echo "$ID" > "$IDS"
mkdir -p "$OUT"
cd "$MSB"

if find "$SKILL_DIR" -type f \( -name '*.py' -o -name '*.sh' \) | grep -q .; then
  echo "== direct (skill ships scripts) =="
  DVG_SANDBOX_IMAGE=dvg/sandbox-synthetic \
  DVG_DIRECT_ENTRYPOINT="$DVG/direct_exec/entrypoint_direct.sh" \
    python3 "$DVG/direct_exec/run_direct.py" --ids "$IDS" --out "$OUT/direct_out"
else
  echo "== direct skipped: no scripts (prose-only skill) =="
fi

echo "== instructed =="
python3 "$DVG/instructed_agent/run_instructed.py" --ids "$IDS" \
  --out "$OUT/instructed_out" --config "$MSB/Configs/llm_config_instructed.json"

if [ "$WITH_AGENT" = "--with-agent" ]; then
  echo "== agent (aligned model) =="
  python3 "$DVG/batch_run.py" --only "$IDS" --out "$OUT/batch_out" --budget 0.5
fi

rm -f "$IDS"
tar -czf /tmp/demo_out.tgz -C "$OUT" .
echo "packed $OUT -> /tmp/demo_out.tgz"
