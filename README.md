# Divergence

Intent–behaviour consistency scoring for autonomous AI agent skills, implemented as an
AGT-pattern evaluator (`DivergenceEvaluator`).

A mostly-pretrained, lightly fine-tuned ML layer that scores whether a skill's declared
description is semantically consistent with its observed action trace, using:

1. Trace normalisation (AGT audit log / sandbox result -> ordered action list)
2. Enriched trace-to-text conversion
3. Sentence-BERT embeddings of description and trace text, cosine similarity -> consistency score.
   The encoder is fine-tuned SetFit-style (contrastive `CosineSimilarityLoss` on description-trace
   pairs, via sentence-transformers; the `setfit` library itself is not used)
4. Structural red-flag rules (`flag_unmentioned_domain`, `flag_credential_access`, `flag_undeclared_action_type`)
5. Logistic regression calibration combining both signals into a final verdict

The same step numbers are used in the project layout below and in the module docstrings.

See **Project layout** below for where each part lives. The original build plan is archived in `notes/archive/Structure.md`.

## Use it as an AGT plugin

Divergence is a pip-installable add-on for the Agent Governance Toolkit (AGT 4.1.0). It is a
**research prototype**: it extends AGT's marketplace installer with a pre-install check, and is
not part of Microsoft's AGT distribution.

```bash
pip install "git+https://github.com/KTECeline/divergence.git"     # Python 3.11+, pulls in AGT 4.1.0
```

The trained model (fine-tuned encoder + calibrator) downloads from Hugging Face on first use
([`KTECeline/divergence-minilm-l6`](https://huggingface.co/KTECeline/divergence-minilm-l6), pinned to a fixed commit: the
v0.1.0 weights; override with `DIVERGENCE_HF_REPO` / `DIVERGENCE_HF_REVISION`). For an offline copy, set `DIVERGENCE_MODEL_DIR` to a folder with the
encoder files plus `calibration_model.json`.

**1. Evaluate only (bring your own trace, nothing is executed):**

```bash
divergence evaluate --skill-md path/to/SKILL.md --trace run.json        # add --json for the result object
```

`--trace` takes a raw sandbox run result, an exported AGT `AuditLog` (`{"entries": [...]}`), a
list of AGT audit entries, or a normalised Divergence trace. `--fail-on-flag` exits 1 on FLAG (CI use).

**2. In Python, in place of AGT's own installer:**

```python
from divergence.evaluator.agt_installer import DivergencePluginInstaller, DivergenceEscalation
from divergence.evaluator.trial_runner import LimaTrialRunner   # or CapturedTraceRunner

installer = DivergencePluginInstaller(plugins_dir, registry, trusted_keys,
                                      trial_runner=LimaTrialRunner("dvg-lab"))
try:
    installer.request_install("some-skill", "path/to/some-skill")  # trial -> Divergence -> AGT install
except DivergenceEscalation as e:
    print(e.assessment.summary())          # FLAG: AGT decision "escalate"; approve() after review
```

**3. Full pre-install check (`divergence install --skill-dir path/to/skill`):** runs the skill in
a sealed sandbox first. This needs the Lima VM sandbox described in `sandbox/setup_notes.md`.
**Run untrusted skills only inside a Linux VM, never directly on Docker Desktop.** Use
`--traces-root DIR` to assess trials captured earlier instead.

Exit codes: 0 allow/installed, 1 flag/blocked (and nothing else), 2 invalid input (a trace,
description or argument that cannot be read), 3 sandbox trial failed or produced no run, 4 model not
found, 5 unexpected error, 6 blocked by AGT's own install checks (`divergence install` only; AGT's
reason is printed). Codes 2 to 5 mean no verdict was produced: an unreadable trace is an error,
never an ALLOW. A run with no observable actions is announced before the verdict ("nothing was
observed during the trial; this is not evidence the skill is safe").
Limits: only behaviour that fires during the trial is seen (time bombs and trigger-gated payloads
are missed); an empty trace means "nothing observed", not "safe"; it measures intent–behaviour
divergence, not maliciousness.

## Research setup (reproducing the experiments)

Two dependency lists, for two purposes:

| File | Versions | Use it to |
|---|---|---|
| `requirements.txt` | exact pins: the environment the reported results were produced on | reproduce the numbers in `results/` |
| `pyproject.toml` | lower bounds only | use or develop the plugin with current libraries |

```bash
python3.11 -m venv .venv
source .venv/bin/activate

# to reproduce the reported results:
pip install -r requirements.txt
pip install -e . --no-deps               # adds the `divergence` command without changing those versions

# or, to use / develop the plugin (newer libraries; scores can differ in the last decimals):
pip install -e ".[research,dev]"
```

## Dataset

The pipeline uses **MalSkillBench** (Guo et al., 2026). Clone the raw, unmodified dataset into
`vendor/MalSkillBench/` (the code reads skills from `vendor/MalSkillBench/Dataset/Skills/`;
see `divergence/config.py`). The local patches applied for sandbox runs are in
`sandbox/malskillbench_patches.diff`.

## Project layout

```
divergence/                 the pip package
├── cli.py                  `divergence evaluate | install`
├── config.py               all paths and constants
├── model_store.py          finds the trained model (local folder or Hugging Face)
├── metrics.py              AUC, bootstrap CIs, McNemar (used by experiments + tests)
│
│   ── the shipped pipeline (runs on every skill) ──
├── preprocessing/          1 normalise_trace  ->  2 trace_to_text  ->  4 structural_flags
├── embedding/              3 encoder + similarity (consistency score); finetune_setfit (training)
├── calibration/            5 logistic_calibrator (score + flags -> probability -> FLAG/ALLOW)
├── evaluator/              DivergenceEvaluator, DivergencePluginInstaller (AGT), trial runners
│
│   ── research only (how the model and the report numbers were made) ──
├── data/                   build run samples from MalSkillBench + traces, leakage-safe splits
├── labelling/              hand-review sheets, merge_labels -> 308-run labelled dataset
├── baselines/              comparison models for Chapter 5
└── experiments/            exp1 ... exp6, one script per report experiment

labels/                     hand-review label CSVs (the ground truth, committed)
notebooks/                  01-07: step-by-step walkthrough of the pipeline (imports divergence/)
sandbox/                    sealed VM runners that executed the skills and captured traces
tests/                      unit tests (`pytest`)
results/                    experiment CSVs (not committed) and figures
notes/                      roadmap, citations; notes/archive/ = superseded planning docs
data/, models/, vendor/     datasets, trained model, MalSkillBench (not committed)
```

## Methodology

CRISP-DM. Phases map to report sections 3.2.3.1–3.2.3.6.
