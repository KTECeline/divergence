---
library_name: sentence-transformers
base_model: sentence-transformers/all-MiniLM-L6-v2
pipeline_tag: sentence-similarity
tags:
- sentence-transformers
- agent-security
- agent-governance-toolkit
---

# Divergence: intent–behaviour consistency model (research prototype)

The trained model for [Divergence](https://github.com/KTECeline/divergence), a pre-install
check that extends the Agent Governance Toolkit (AGT 4.1.0) marketplace installer. It scores
whether an AI agent skill's **declared description** is consistent with its **observed
behaviour** in a sandbox trial run. Load it with the `divergence-agt` package rather than directly:

```bash
pip install "git+https://github.com/KTECeline/divergence.git"
divergence evaluate --skill-md SKILL.md --trace run.json
```

## Contents
- Sentence encoder: `all-MiniLM-L6-v2` fine-tuned with `CosineSimilarityLoss` on
  (description, enriched trace text) pairs. 130 labelled runs, 12 epochs, seed 42.
- `calibration_model.json`: logistic regression over the consistency score and three
  structural red flags (unmentioned domain, credential access, undeclared action type).
  FLAG at probability ≥ 0.5.

## Evaluation (held-out test split, 117 runs, used once)
AUC 0.913 (95% CI 0.854–0.962), F1 0.804, false-alarm rate 0.10. See the repository for the
baselines, ablations and control experiments.

## Intended use and limits
- Research prototype; not a production security control.
- It measures **intent–behaviour divergence**, not maliciousness: a malicious skill that
  accurately describes its behaviour is expected to pass.
- It only sees behaviour that fires during the trial run. Time bombs, trigger-gated and
  reply-only payloads are missed, and an empty trace means "nothing observed", not "safe".
- Description vocabulary rules are English-only.

## Training data
Derived from MalSkillBench (Guo et al., 2026; academic research use) plus traces captured in
the author's sealed sandbox. No training examples are included in this repository.
