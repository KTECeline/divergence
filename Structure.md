# Divergence — Architecture & Build Plan

**Project:** Intent–behaviour consistency evaluator for AI agent skills, integrated as an AGT (Agent Governance Toolkit) evaluator.
**Version:** v8 (post 3rd supervisor meeting)
**Methodology:** CRISP-DM only (no Agile/hybrid framing)

---

## 1. One-sentence description

A mostly-pretrained, lightly fine-tuned ML layer that sits on top of AGT and scores whether a skill's declared description is semantically consistent with its observed AGT action trace, using sentence embeddings (fine-tuned via few-shot SetFit), cosine similarity, hand-specified structural red-flag rules, and a trained logistic regression calibration layer that combines both signals into a final verdict.

---

## 2. Current phase

**Phase 1 (now):** Build and validate the full pipeline against MalSkillBench alone. No OpenClaw/AGT dependency needed yet.
**Phase 2 (later):** Set up OpenClaw + AGT sandbox, capture supplementary traces, fold into hybrid dataset, run live demo (Experiment 5).

Do not block Phase 1 work on Phase 2 setup — pipeline must run standalone first (safety-net principle from the build guide).

---

## 3. Project directory structure

```
divergence/
├── data/
│   ├── raw/
│   │   └── malskillbench/              # raw MalSkillBench dataset (unmodified)
│   ├── processed/
│   │   ├── enriched_traces/            # trace -> enriched text output
│   │   ├── structural_flags/           # per-sample flag results (json/csv)
│   │   └── splits/
│   │       ├── finetune.jsonl
│   │       ├── calibration.jsonl
│   │       └── held_out_test.jsonl
│   └── supplementary/                  # Phase 2: OpenClaw/AGT captured traces
│
├── src/
│   ├── __init__.py
│   ├── config.py                       # paths, model names, thresholds, seeds
│   │
│   ├── data/
│   │   ├── loader.py                   # load + parse MalSkillBench
│   │   ├── splitter.py                 # fine-tune / calibration / held-out split logic
│   │   └── schema.py                   # dataclass/pydantic schema for a "skill sample"
│   │
│   ├── preprocessing/
│   │   ├── trace_to_text.py            # Option 1: enriched trace -> text conversion
│   │   └── structural_flags.py         # Option 2: rule-based red-flag checks
│   │
│   ├── embedding/
│   │   ├── encoder.py                  # Sentence-BERT load + encode wrapper
│   │   ├── finetune_setfit.py          # Step 0: SetFit few-shot fine-tune
│   │   └── similarity.py               # cosine similarity scoring
│   │
│   ├── calibration/
│   │   └── logistic_calibrator.py      # Step 6: logistic regression combiner
│   │
│   ├── evaluator/
│   │   └── divergence_evaluator.py     # DivergenceEvaluator class (AGT-pattern shape)
│   │
│   ├── baselines/
│   │   ├── agt_only.py
│   │   ├── behaviour_only.py
│   │   ├── text_only.py
│   │   └── llm_as_judge.py
│   │
│   └── experiments/
│       ├── exp1_baseline_comparison.py
│       ├── exp2_ablation.py
│       ├── exp2b_finetune_ablation.py
│       ├── exp3_attack_type_breakdown.py
│       └── exp4_embedding_model_comparison.py   # optional/bonus
│
├── notebooks/
│   ├── 01_data_understanding.ipynb     # EDA: class balance, taxonomy distribution
│   ├── 02_trace_to_text_dev.ipynb      # template development/testing
│   ├── 03_structural_flags_dev.ipynb   # flag rule development/testing
│   └── 04_results_analysis.ipynb
│
├── models/
│   ├── finetuned_embedding/            # saved SetFit-fine-tuned model
│   └── calibration_model.pkl           # saved logistic regression
│
├── results/
│   ├── exp1_results.csv
│   ├── exp2_ablation_results.csv
│   ├── exp2b_finetune_delta.csv
│   ├── exp3_attack_breakdown.csv
│   └── figures/
│
├── sandbox/                            # Phase 2: OpenClaw/AGT integration
│   ├── setup_notes.md
│   └── demo_pipeline.py                # Experiment 5 live demo
│
├── tests/
│   ├── test_trace_to_text.py
│   ├── test_structural_flags.py
│   └── test_evaluator.py
│
├── requirements.txt
└── README.md
```

---

## 4. Per-skill pipeline (runtime flow)

```
INPUT: skill description text + AGT-style audit log (action trace)

Step 1 — Encode description
   description text -> fine-tuned Sentence-BERT -> Vector_A

Step 2 — Convert trace to enriched text (mandatory, Option 1)
   raw trace -> rule-based enrichment template -> enriched text
   e.g. "reads a file, then sends data to an external, previously
         unseen domain, then writes a file"
   (NOT a flat template — must name sensitive action types explicitly)

Step 3 — Encode enriched trace text
   enriched text -> same fine-tuned Sentence-BERT -> Vector_B

Step 4 — Semantic consistency score
   cosine_similarity(Vector_A, Vector_B) -> score in [0,1]

Step 5 — Structural red-flag features (mandatory, Option 2, no ML)
   - flag_unmentioned_domain
   - flag_credential_access
   - flag_undeclared_action_type

Step 6 — Calibration (trained)
   logistic_regression([similarity, flag1, flag2, flag3])
   -> probability-of-suspicious -> ALLOW / FLAG verdict

OUTPUT (DivergenceEvaluator.evaluate() result object):
   result.consistency_score
   result.structural_flags
   result.verdict
   result.reasoning
```

This mirrors AGT's own `PromptDefenseEvaluator` shape (`.score`, `.missing`, `.compliance`) — cite this precedent in 2.4.3.4.

---

## 5. One-time setup pipeline (Step 0, runs once before deployment)

```
1. Collect fine-tune split (labelled description/behaviour pairs, consistent + inconsistent)
2. Fine-tune Sentence-BERT via SetFit contrastive objective on fine-tune split
   -> saved as models/finetuned_embedding/
3. Fit logistic regression calibration layer on calibration split
   -> saved as models/calibration_model.pkl
4. Both artifacts loaded once, reused for every skill scanned afterward
```

---

## 6. Build order (Phase 1, MalSkillBench only)

- [ ] **1. Environment setup** — repo skeleton, `requirements.txt` (sentence-transformers, setfit, scikit-learn, pandas, docker sdk if needed later)
- [ ] **2. Data loader** (`src/data/loader.py`) — parse MalSkillBench into your schema (description, trace, label, taxonomy tags)
- [ ] **3. Data understanding EDA** (`notebooks/01_data_understanding.ipynb`) — class balance (3,944 malicious / 4,000 benign), taxonomy distribution across the 108 cells, sample trace inspection
- [ ] **4. Data splitter** (`src/data/splitter.py`) — fine-tune / calibration / held-out test, no leakage
- [ ] **5. Trace-to-text conversion** (`src/preprocessing/trace_to_text.py`) — enriched rule-based template; this is your biggest engineering task, build + test iteratively in `notebooks/02_trace_to_text_dev.ipynb`
- [ ] **6. Structural flag rules** (`src/preprocessing/structural_flags.py`) — three boolean flags, test against hand-crafted cases in `notebooks/03_structural_flags_dev.ipynb`
- [ ] **7. Pretrained-only pipeline** (encoder + similarity, no fine-tune yet) — confirm end-to-end run works; this is your safety net
- [ ] **8. SetFit fine-tune** (`src/embedding/finetune_setfit.py`) — run on fine-tune split, save model, log loss curve
- [ ] **9. Calibration layer** (`src/calibration/logistic_calibrator.py`) — fit on calibration split
- [ ] **10. DivergenceEvaluator class** (`src/evaluator/divergence_evaluator.py`) — wraps steps 1–6 into the AGT-pattern `.evaluate()` interface
- [ ] **11. Baselines** — AGT-only, behaviour-only, text-only, LLM-as-judge (all non-trained)
- [ ] **12. Experiment 1** — baseline comparison + McNemar's test, held-out test split only
- [ ] **13. Experiment 2 / 2b** — ablations (structural flags, trace enrichment, fine-tuning delta)
- [ ] **14. Experiment 3** — attack-type breakdown across taxonomy
- [ ] **15. (Optional) Experiment 4** — embedding model comparison
- [ ] **16. Tests** — unit tests for trace-to-text and structural flags especially (these are your custom logic, most likely to have edge-case bugs)

## 7. Build order (Phase 2, once Phase 1 is stable)

- [ ] Set up OpenClaw + AGT sandbox, pin exact AGT version
- [ ] Capture supplementary skill traces from your own sandbox
- [ ] Fold supplementary traces into hybrid dataset (`data/supplementary/`)
- [ ] Re-run key experiments on hybrid dataset, compare to MalSkillBench-only results
- [ ] Build live demo pipeline (`sandbox/demo_pipeline.py`) — Experiment 5
- [ ] Wire `DivergenceEvaluator` into AGT's actual pre-policy evaluator hook

---

## 8. Key naming/citation anchors to keep consistent in code + report

- Dataset: **MalSkillBench** (Guo et al., 2026)
- AGT precedent evaluator: **`PromptDefenseEvaluator`**
- Integration subsystem: **"Agent Marketplace — Plugin governance and trust scoring"**
- Methodology: **CRISP-DM only**, phases mapped to 3.2.3.1–3.2.3.6
- Your evaluator class name: **`DivergenceEvaluator`**, output fields `.consistency_score`, `.structural_flags`, `.verdict`, `.reasoning`

---

## 9. Notes for Claude Code

- Start with items 1–6 (setup through structural flags) — these are fully unblocked by MalSkillBench alone.
- Keep `trace_to_text.py` and `structural_flags.py` easily testable in isolation — write unit tests as you go, not at the end, since these are your original contribution and most likely source of bugs/examiner questions.
- Don't touch `sandbox/` until Phase 1 experiments (Exp 1, 2, 2b, 3) are producing results you trust.