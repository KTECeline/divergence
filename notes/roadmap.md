# Divergence — roadmap from sandbox to submission (written 2026-10-19)

## End goal

At submission you need three things:

1. **A working `DivergenceEvaluator`.** You give it a skill's description and the
   trace of what the skill actually did. It returns `consistency_score`,
   `structural_flags`, `verdict` and `reasoning`. It is built to AGT's
   `PromptDefenseEvaluator` contract and runs inside your own AGT sandbox.
2. **Evidence that it works, and where it doesn't.** Experiments that answer the
   five examiner questions: theory, label validity, generalisation, what the ML
   adds beyond rules, and leakage.
3. **The report and viva**, written from that evidence (Ch. 4 implementation,
   Ch. 5 results).

Everything below feeds one of those three.

## Key point: the sandbox is on the critical path now

MalSkillBench ships **skills** (`SKILL.md` + scripts), not **traces**.
`Logs/` is empty and no strace or audit output is included. The "behaviour"
half of every (description, behaviour) pair has to be produced by running the
skills in the VM sandbox. So the sandbox isn't a Phase 2 extra: it produces
your core dataset. `Structure.md` §2 ("no sandbox needed for Phase 1") needs
updating to say this.

## Stages (CRISP-DM phase in brackets)

### Stage 1 — Finish the sandbox *(Data Understanding)*
- [x] VM, Docker, sealed network, INetSim, fake DNS, key proxy, runner patch
- [ ] Smoke test on the benign skill `12306`
- [ ] Model pilot: 10 benign + 10 malicious skills. Fix the model and provider and record them
- **Done when:** a malicious skill run shows its payload in strace, and that
  activity only reached INetSim.

### Stage 2 — Generate traces *(Data Understanding → Preparation)*
- Write a batch runner (resumable; one JSON of evidence per skill)
- Sample with stratification, not all 7,945: about **1,000 malicious spread across
  the taxonomy cells + 1,000 benign**. Estimated cost is about $5–15 (measure it in the pilot)
- Use the `scripts/` split as a sampling dimension: only 568/4,000 benign and
  1,707/3,945 malicious skills ship scripts. The rest are instructions-only, so
  their trace shows the agent's behaviour, not code. Report results separately
  for the two groups
- Log the outcome of every run: loaded / refused / timed out / error. The refusal
  rate is a finding in its own right; report it, don't hide it
- Copy the evidence back to the Mac → `data/raw/traces/`
- **Done when:** about 2,000 usable (description, trace, label, taxonomy) records exist.

### Stage 3 — Prepare the data *(Data Preparation)*
- `loader.py`: SKILL.md description + evidence JSON → `schema.py` record
- Trace normaliser: strace/inotify events → an ordered action list. This is your
  "AGT-style audit log" format, and it is the same format the AGT run produces in Stage 6
- **Group-aware split first** (viva priority #1). Keep generated variants of the
  same base skill (e.g. `…__CI_B4`, `…__PI_B10`) in one split, otherwise
  near-duplicates leak across splits
- **Find where the taxonomy labels live.** Only 1,300 malicious folders encode
  them in the name (`__CI_` 575, `__PI_` 395, `__MIXED_` 330, plus a behaviour
  code such as `B4`). The other 2,645 (e.g. `0x-swap`) have only `SKILL.md`, with
  no label in the name and no `_meta.json`. Check the paper / repo for a label file
  before relying on the "108 cells"
- EDA notebook: class balance, taxonomy coverage, trace length

### Stage 4 — Build the model step by step *(Modelling)*
Build in this order, and get each piece working before adding the next:
1. `trace_to_text.py` (+ unit tests, collision check)
2. `structural_flags.py` (+ unit tests)
3. Pretrained Sentence-BERT + cosine similarity (**safety-net result**)
4. SetFit fine-tune on the fine-tune split
5. Logistic-regression calibration on the calibration split
6. Wrap it all in `DivergenceEvaluator.evaluate()`

### Stage 5 — Evaluate *(Evaluation)*. Held-out test split only
- Exp 1: baselines (AGT-only, behaviour-only, text-only, capability-overlap,
  LLM-as-judge) + McNemar's test
- Exp 2/2b: ablations (flags, enrichment, fine-tuning delta). This answers
  "what does the ML add?"
- Exp 5: controls (swapped description, disclosed payload). Divergence ≠ malice
- Exp 6: held-out behaviour class / attack vector. Generalisation
- Failure analysis: 20–30 errors, grouped by cause
- (Proposed scope tiering, still waiting for your OK: merge Exp 3 into Exp 1,
  make Exp 4 optional.)

### Stage 6 — Deploy in AGT *(Deployment)*
- Install AGT in the VM with a **pinned** version
  (`pip install "agent-governance-toolkit[full]==X.Y.Z"`) and record it
- Run a small set of skills through **OpenClaw + AGT**. This gives the supplementary
  traces and a cross-source test (MalSkillBench traces come from OpenCode, these from OpenClaw)
- Register `DivergenceEvaluator` as a pre-policy evaluator. Its output becomes
  evidence fields on AGT's ALLOW/DENY/… decision
- `sandbox/demo_pipeline.py` = Experiment 7, the live demo for the viva

### Stage 7 — Write up
- Ch. 4 (implementation/safety): from `sandbox/setup_notes.md`
- Ch. 5 (results): from `results/*.csv` + figures
- Wording rules: say "research prototype" and "sandbox deployment", not
  production. Don't use "multimodal". The survey counts as design validation.

## If you're short on time, cut in this order
Exp 4 → latency table → Exp 3 (fold it into Exp 1) → OpenClaw cross-source test
(keep the demo). **Never cut** the leakage-free split, Exp 1, Exp 2/2b or the demo.
