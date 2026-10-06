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

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Dataset

Phase 1 uses **MalSkillBench** (Guo et al., 2026) — place the raw, unmodified dataset in
`data/raw/malskillbench/`. See the README in that folder.

## Project layout

- `src/` — pipeline source (data loading, preprocessing, embedding, calibration, evaluator, baselines, experiments)
- `notebooks/` — EDA and iterative development notebooks
- `data/` — raw / processed / supplementary datasets (not committed)
- `models/` — saved fine-tuned embedding model and calibration model
- `results/` — experiment outputs and figures
- `sandbox/` — Phase 2 OpenClaw/AGT integration (do not touch until Phase 1 experiments are stable)
- `tests/` — unit tests (trace-to-text and structural flags especially)

## Methodology

CRISP-DM. Phases map to report sections 3.2.3.1–3.2.3.6.
