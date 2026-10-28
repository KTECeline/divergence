# Direct-execution mode (Stage 3, second execution mode)

## Why
About 74% of malicious agent runs are refusals: the agent read the skill, saw
the threat and stopped, so its trace shows no payload. The model learns
"inconsistent" only from runs where the payload actually ran, and those are
rare (~62). Direct mode removes the agent's decision: it runs each skill's own
scripts straight under `strace`, so the payload runs and is traced. No LLM is
involved, so it costs **$0** and never refuses.

This is a **complementary** evaluation, not a replacement. A script that
behaves badly when run directly does not prove the agent would have run it. The
report keeps the two modes separate: `batch_out/` (agent) vs `direct_out/`.

## Containment (unchanged from the agent sandbox)
Same sealed `dvg-isolated` network (no route out, INetSim answers and logs every
request), `--cap-drop ALL`, `--pids-limit`, memory/cpu caps. The only change is
the entrypoint: `entrypoint_direct.sh` replaces OpenCode, swapped in with
`--entrypoint` via the `DVG_DIRECT_ENTRYPOINT` env var that `sandbox.py` reads.
Run it on the synthetic-user image (`dvg/sandbox-synthetic`) so credential- and
exfiltration payloads have fake data to find; the `DVGCANARY` marker in the
INetSim logs then proves what left the container.

## Rules (so the result survives a viva)
1. Run **benign** skills through here too (they are in the id lists), or the
   model learns "direct-mode trace == malicious".
2. **Prompt-injection skills (PI, B10–B15) have no script to run**, so direct
   mode does not apply to them; they stay agent-only, mostly out of scope.
3. Each direct run inherits its skill's split from `split_assignment.csv`, so
   there is no leakage; the frozen 802/400/800 split is untouched.
4. Agent and direct runs are never merged silently.

## Files
- `entrypoint_direct.sh` — runs every `scripts/*.py` and `*.sh` the skill ships,
  each from its own dir, under one `strace -f`, with per-script and overall
  timeouts. Writes the same evidence files the agent entrypoint does, so
  `sandbox.py._collect_evidence` and `src/preprocessing/normalise_trace.py` read
  it unchanged. `normalise()` detects "no tool calls" and builds the action list
  from the strace events alone (ordered by pid).
- `run_direct.py` — driver. Reuses `DockerSandbox` (same containment + evidence),
  iterates a `<label>/<skill>` id file, writes `direct_out/results/...json` and
  `direct_out/summary.csv`. Resumable.

## Run (inside the VM)
```
# copy over (from the Mac):
#   tar czf /tmp/direct.tgz sandbox/direct_exec sandbox/synthetic_user vendor/batch_run.py \
#       vendor/MalSkillBench/Core/verification/sandbox.py
#   limactl copy /tmp/direct.tgz dvg-lab:/tmp/
mkdir -p /tmp/d && tar xzf /tmp/direct.tgz -C /tmp/d
cp -r /tmp/d/sandbox/direct_exec ~/dvg/direct_exec
cp -r /tmp/d/sandbox/synthetic_user ~/dvg/synthetic_user
cp /tmp/d/vendor/MalSkillBench/Core/verification/sandbox.py ~/dvg/MalSkillBench/Core/verification/sandbox.py
docker build -t dvg/sandbox-synthetic ~/dvg/synthetic_user   # if not built yet

source ~/dvg/.venv/bin/activate && cd ~/dvg/MalSkillBench
DVG_SANDBOX_IMAGE=dvg/sandbox-synthetic \
DVG_DIRECT_ENTRYPOINT=~/dvg/direct_exec/entrypoint_direct.sh \
DVG_MSB_ROOT=~/dvg/MalSkillBench \
python3 ~/dvg/direct_exec/run_direct.py \
    --ids ~/dvg/synthetic_user/pilot_ids.txt --out ~/dvg/direct_out

docker cp inetsim:/var/log/inetsim ~/dvg/direct_out/netlogs
grep -rl DVGCANARY ~/dvg/direct_out/netlogs 2>/dev/null   # proof of exfiltration, if any
```
### Id lists
- `../synthetic_user/pilot_ids.txt` — 35 skills, ~5 min. Run this first to confirm the pipeline.
- `all_ids.txt` — **all 573 skills that ship runnable scripts** (414 malware + 159 benign).
  The other 1,430 skills in the dataset are prose-only (the "payload" is agent
  instructions in SKILL.md, no code), so direct mode has nothing to run for them
  and they are omitted. That split (573 with code / 1,430 prose-only) is itself a
  reportable finding about where these attacks live.

### Full run (a few hours, free, resumable — do it overnight)
```
caffeinate -dimsu limactl shell dvg-lab      # keep the Mac awake (run on the Mac)
# ...then inside the VM:
source ~/dvg/.venv/bin/activate && cd ~/dvg/MalSkillBench
DVG_SANDBOX_IMAGE=dvg/sandbox-synthetic \
DVG_DIRECT_ENTRYPOINT=~/dvg/direct_exec/entrypoint_direct.sh \
DVG_MSB_ROOT=~/dvg/MalSkillBench \
python3 ~/dvg/direct_exec/run_direct.py \
    --ids ~/dvg/direct_exec/all_ids.txt --out ~/dvg/direct_out
```
Ctrl+C / crash / reboot are all safe: each finished skill is one row in
`direct_out/summary.csv`, and a rerun skips rows already there. After it
finishes, copy the INetSim logs and grep for the canary:
```
docker cp inetsim:/var/log/inetsim ~/dvg/direct_out/netlogs
grep -rl DVGCANARY ~/dvg/direct_out/netlogs 2>/dev/null   # payloads that exfiltrated planted data
```
Then transfer `direct_out/` to the Mac the same way Stage 2 data was moved
(`sandbox/setup_notes.md` Step K).
