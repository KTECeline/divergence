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
your core dataset. `Structure.md` §2 now says this (updated 2026-10-21).

## Stages (CRISP-DM phase in brackets)

### Stage 1 — Finish the sandbox *(Data Understanding)*
- [x] VM, Docker, sealed network, INetSim, fake DNS, key proxy, runner patch
- [ ] Smoke test on the benign skill `12306`
- [x] Agent-model pilot (done 2026-10-20, DeepSeek V4.1 Flash chosen): the same 20 skills × 3 agent LLMs (`pilot_run.py --model …`),
      compared on criteria fixed in advance → choose one, justify it in Ch. 4.2 (Data Collection)
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
- **Done 2026-10-21.** 2,003 runs (1,003 malicious across all 108 cells + 179
  wild, 1,000 benign), 0 escapes, in `data/raw/traces/` (archive SHA-256 in
  setup_notes Step K). Provisional outcomes: malicious 358 proceeded / 519
  declined / 113 no execution; benign 720 attempted / 240 no execution;
  31 error_or_hang. Only ~36 % of malicious runs show the payload behaviour,
  so Stage 3 labels runs by what was observed.

### Stage 3 — Prepare the data *(Data Preparation)*
- `loader.py`: SKILL.md description + evidence JSON → `schema.py` record
- Trace normaliser: strace/inotify events → an ordered action list. This is your
  "AGT-style audit log" format, and it is the same format the AGT run produces in Stage 6
- **Group-aware split first** (viva priority #1). Keep generated variants of the
  same base skill (e.g. `…__CI_B4`, `…__PI_B10`) in one split, otherwise
  near-duplicates leak across splits
- **Taxonomy labels → `Dataset/Skills/malware/_source_inventory.txt`** (found
  2026-10-20). Each line is `SOURCE  name  <-  origin`. For GENERATED samples the
  origin path holds the full taxonomy, e.g.
  `generated_malicious/PI/B5/full_camouflage_…` = vector / behaviour class /
  insertion strategy. Counts match the paper: GENERATED 3,214 (CI 1,346 · PI 1,300 ·
  MIXED 568), WILD 703, TEST 27, with exactly **108 distinct cells**. The folder-name
  suffix (`__CI_B4`) only marks duplicates and isn't the label source; most
  generated samples have no suffix. WILD samples only carry an author. **Exclude
  the 27 TEST samples** from the dataset. Parser: `load_inventory()` in `vendor/pilot_run.py`
  (move it into `src/data/loader.py` in Stage 3)
- EDA notebook: class balance, taxonomy coverage, trace length

**Stage 3 progress (2026-10-21)**
- [x] `src/preprocessing/normalise_trace.py`: tool calls are the ordered backbone;
      strace effects attributed to the bash call through the process tree
      (95.5 % of bash calls matched); agent text and OpenCode's own activity dropped
- [x] `src/data/outcome.py`: behaviour signals + provisional outcome (replaces
      batch_run.py's heuristic, which counted `pip`/`diff` as "ran skill code")
- [x] `src/data/loader.py` -> `data/processed/samples.jsonl` (2,003 runs; strips the
      generator marker found in 888 malicious SKILL.md files and 0 benign ones)
- [x] `src/data/splitter.py`: group_key + identical-description union-find,
      StratifiedGroupKFold -> 802 / 400 / 800, leakage check passes; 1 run
      excluded (no description)
- [x] `src/data/review_sheet.py` -> `data/processed/review/` (181 rows: 71 A, 110 B)
- [x] tests: 26 pass
- [ ] **Hand review (you)** -> final labels -> decide the positive class
- [ ] EDA notebook
- **Key finding:** the agent ran shipped scripts for 111/142 benign but 15/431
  malicious skills, and declined for security reasons in ~740 of 1,003
  malicious runs. Real payload behaviour is rare (rules: ~62 candidates).
  How to get enough positives is an open decision (see the 2026-10-21 notes).

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
- **Exp 4 (embedding model comparison) is now CORE, not optional.** The APU
  guideline (CSDA Ch. 4.5 "Model Building with Technique 1…4", Ch. 5.2
  "Evaluation of Model ABC / XYZ…") expects several models to be built and
  compared, with a justification for the final choice. Compare at least 3
  sentence encoders (e.g. MiniLM, MPNet, a BGE/E5-class model), each pretrained
  vs SetFit-fine-tuned, on the same split, and justify the winner on accuracy,
  calibration and inference speed.
- (Still proposed: merge Exp 3 into Exp 1.)

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
latency table → Exp 3 (fold it into Exp 1) → OpenClaw cross-source test
(keep the demo). **Never cut** the leakage-free split, Exp 1, Exp 2/2b or the demo.
