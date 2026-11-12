# Divergence

Intent–behaviour consistency scoring for autonomous AI agent skills, implemented as an
AGT-pattern evaluator (`DivergenceEvaluator`).

A mostly-pretrained, lightly fine-tuned ML layer that scores whether a skill's declared
description is semantically consistent with its observed action trace, using:

1. Sentence-BERT embeddings (few-shot fine-tuned via SetFit)
2. Enriched trace-to-text conversion
3. Cosine similarity scoring
4. Structural red-flag rules (`flag_unmentioned_domain`, `flag_credential_access`, `flag_undeclared_action_type`)
5. Logistic regression calibration combining both signals into a final verdict

See [Structure.md](Structure.md) for the full architecture and build plan.

## Use it as an AGT plugin

Divergence is a pip-installable add-on for the Agent Governance Toolkit (AGT 4.1.0). It is a
**research prototype**: it extends AGT's marketplace installer with a pre-install check, and is
not part of Microsoft's AGT distribution.

```bash
pip install "git+https://github.com/KTECeline/divergence.git"     # Python 3.11+, pulls in AGT 4.1.0
```

The trained model (fine-tuned encoder + calibrator) downloads from Hugging Face on first use
([`KTECeline/divergence-minilm-l6`](https://huggingface.co/KTECeline/divergence-minilm-l6), pinned to the
v0.1.0 commit; override with `DIVERGENCE_HF_REPO` / `DIVERGENCE_HF_REVISION`). For an offline copy, set `DIVERGENCE_MODEL_DIR` to a folder with the
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

Exit codes: 0 allow/installed, 1 flag/blocked, 3 sandbox trial failed, 4 model not found.
Limits: only behaviour that fires during the trial is seen (time bombs and trigger-gated payloads
are missed); an empty trace means "nothing observed", not "safe"; it measures intent–behaviour
divergence, not maliciousness.

## Research setup (reproducing the experiments)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e ".[research,dev]"
```

## Dataset

Phase 1 uses **MalSkillBench** (Guo et al., 2026) — place the raw, unmodified dataset in
`data/raw/malskillbench/`. See the README in that folder.

## Project layout

- `divergence/` — the installable package: pipeline source (data loading, preprocessing, embedding, calibration, evaluator, baselines, experiments), `cli.py` (the `divergence` command), `model_store.py` (where the trained model is loaded from)
- `notebooks/` — EDA and iterative development notebooks
- `data/` — raw / processed / supplementary datasets (not committed)
- `models/` — saved fine-tuned embedding model and calibration model
- `results/` — experiment outputs and figures
- `sandbox/` — Phase 2 OpenClaw/AGT integration (do not touch until Phase 1 experiments are stable)
- `tests/` — unit tests (trace-to-text and structural flags especially)

## Methodology

CRISP-DM. Phases map to report sections 3.2.3.1–3.2.3.6.
