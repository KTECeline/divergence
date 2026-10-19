# Graph Report - Divergence  (2026-10-19)

## Corpus Check
- 46 files · ~11,931 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 194 nodes · 176 edges · 37 communities (21 shown, 16 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `75abf638`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_SkillSample|SkillSample]]
- [[_COMMUNITY_DIVERGENCE v8|DIVERGENCE v8]]
- [[_COMMUNITY_Divergence — Architecture & Build Plan|Divergence — Architecture & Build Plan]]
- [[_COMMUNITY_StructuralFlags|StructuralFlags]]
- [[_COMMUNITY_divergence_evaluator.py|divergence_evaluator.py]]
- [[_COMMUNITY_LogisticCalibrator|LogisticCalibrator]]
- [[_COMMUNITY_trace_to_enriched_text|trace_to_enriched_text]]
- [[_COMMUNITY_Encoder|Encoder]]
- [[_COMMUNITY_Citation notes (drafted, not yet placed in the report)|Citation notes (drafted, not yet placed in the report)]]
- [[_COMMUNITY_similarity.py|similarity.py]]
- [[_COMMUNITY_demo_pipeline.py|demo_pipeline.py]]
- [[_COMMUNITY_agt_only.py|agt_only.py]]
- [[_COMMUNITY_behaviour_only.py|behaviour_only.py]]
- [[_COMMUNITY_llm_as_judge.py|llm_as_judge.py]]
- [[_COMMUNITY_text_only.py|text_only.py]]
- [[_COMMUNITY_finetune_setfit.py|finetune_setfit.py]]
- [[_COMMUNITY_exp1_baseline_comparison.py|exp1_baseline_comparison.py]]
- [[_COMMUNITY_exp2_ablation.py|exp2_ablation.py]]
- [[_COMMUNITY_exp2b_finetune_ablation.py|exp2b_finetune_ablation.py]]
- [[_COMMUNITY_exp3_attack_type_breakdown.py|exp3_attack_type_breakdown.py]]
- [[_COMMUNITY_exp4_embedding_model_comparison.py|exp4_embedding_model_comparison.py]]
- [[_COMMUNITY_exp5_control_experiments.py|exp5_control_experiments.py]]
- [[_COMMUNITY_exp6_holdout_generalisation.py|exp6_holdout_generalisation.py]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_00_toy_demo.py|00_toy_demo.py]]
- [[_COMMUNITY_setup_notes|setup_notes.md]]
- [[_COMMUNITY_smoke_test.py|smoke_test.py]]
- [[_COMMUNITY_Stages (CRISP-DM phase in brackets)|Stages (CRISP-DM phase in brackets)]]
- [[_COMMUNITY_instructions_for_record|instructions_for_record.md]]

## God Nodes (most connected - your core abstractions)
1. `Sandbox build log` - 14 edges
2. `SkillSample` - 10 edges
3. `Divergence — Architecture & Build Plan` - 10 edges
4. `DIVERGENCE v8` - 8 edges
5. `Stages (CRISP-DM phase in brackets)` - 8 edges
6. `StructuralFlags` - 6 edges
7. `LogisticCalibrator` - 5 edges
8. `compute_structural_flags()` - 5 edges
9. `Updated Section 5 Equivalent — How Divergence Integrates With AGT (v8)` - 5 edges
10. `Divergence` - 5 edges

## Surprising Connections (you probably didn't know these)
- `test_flags_raised_names()` --calls--> `StructuralFlags`  [EXTRACTED]
  tests/test_structural_flags.py → src/preprocessing/structural_flags.py
- `test_not_yet_implemented()` --calls--> `compute_structural_flags()`  [EXTRACTED]
  tests/test_structural_flags.py → src/preprocessing/structural_flags.py
- `test_result_object_shape()` --calls--> `DivergenceResult`  [EXTRACTED]
  tests/test_evaluator.py → src/evaluator/divergence_evaluator.py
- `test_not_yet_implemented()` --calls--> `trace_to_enriched_text()`  [EXTRACTED]
  tests/test_trace_to_text.py → src/preprocessing/trace_to_text.py
- `build_proxy_labelling_sheet()` --references--> `SkillSample`  [EXTRACTED]
  src/data/control_sets.py → src/data/schema.py

## Import Cycles
- None detected.

## Communities (37 total, 16 thin omitted)

### Community 0 - "SkillSample"
Cohesion: 0.14
Nodes (16): build_disclosed_payload_set(), build_proxy_labelling_sheet(), build_swapped_description_set(), Build the control sets that separate inconsistency from maliciousness.  Used by, Sample n malicious skills into a CSV for hand-labelling.      Columns: sample_id, Benign trace paired with a different benign skill's description.      Inconsiste, Malicious trace paired with a description that honestly states the payload., load_malskillbench() (+8 more)

### Community 1 - "DIVERGENCE v8"
Cohesion: 0.12
Nodes (16): AGT technical sources (new), Chapter 2 additions confirmed still needed (from earlier session, unchanged), DIVERGENCE v8, graphify, Methodology sources (new, from Chapter 3 restructure), Reference Library Additions (v8), Technical grounding (for 2.4.3.4), The integration flow (v8) (+8 more)

### Community 2 - "Divergence — Architecture & Build Plan"
Cohesion: 0.12
Nodes (15): Dataset, Divergence, Methodology, Project layout, Setup, 1. One-sentence description, 2. Current phase, 3. Project directory structure (+7 more)

### Community 3 - "StructuralFlags"
Cohesion: 0.24
Nodes (8): compute_structural_flags(), Structural red-flag rules (pipeline Step 5, Option 2 — no ML).  Build order item, Names of the flags that fired, for the evaluator's result object., Run the three rule-based red-flag checks on a description/trace pair., StructuralFlags, Unit tests for structural red-flag rules (build order item 16).  Cover hand-craf, test_flags_raised_names(), test_not_yet_implemented()

### Community 4 - "divergence_evaluator.py"
Cohesion: 0.27
Nodes (6): DivergenceEvaluator, DivergenceResult, DivergenceEvaluator — the AGT-pattern evaluator wrapping the full pipeline.  Bui, Wraps pipeline Steps 1-6: encode description, enrich + encode trace,     cosine, Unit tests for DivergenceEvaluator (build order item 16)., test_result_object_shape()

### Community 5 - "LogisticCalibrator"
Cohesion: 0.25
Nodes (3): LogisticCalibrator, Logistic regression calibration layer (pipeline Step 6).  Build order item 9. Fi, Probability that the skill is suspicious.

### Community 6 - "trace_to_enriched_text"
Cohesion: 0.38
Nodes (5): Enriched trace-to-text conversion (pipeline Step 2, Option 1).  Build order item, Convert a raw action trace into enriched descriptive text.      Example output:, trace_to_enriched_text(), Unit tests for enriched trace-to-text conversion (build order item 16).  Write t, test_not_yet_implemented()

### Community 7 - "Encoder"
Cohesion: 0.25
Nodes (4): Central configuration: paths, model names, thresholds, seeds.  Every module read, Encoder, Sentence-BERT load + encode wrapper (pipeline Steps 1 and 3).  Build order item, Thin wrapper around a sentence-transformers model.      Loads either the pretrai

### Community 8 - "Citation notes (drafted, not yet placed in the report)"
Cohesion: 0.50
Nodes (3): Citation notes (drafted, not yet placed in the report), ClawHub Security Signals — motivating evidence (not used as data), Phase 1 trace capture — OpenCode-as-agent-proxy (methodology/scope note)

### Community 9 - "similarity.py"
Cohesion: 0.50
Nodes (3): consistency_score(), Cosine similarity scoring between description and enriched-trace vectors (pipeli, cosine_similarity(Vector_A, Vector_B) -> score in [0, 1].

### Community 25 - "setup_notes.md"
Cohesion: 0.12
Nodes (15): Environment (recorded 2026-10-19), Isolation checks (2026-10-19), LLM choice for the agent (OpenCode) — researched 2026-10-19, Pending, Phase 2 — OpenClaw/AGT sandbox setup notes, Sandbox build log, Step A — Copy MalSkillBench into the VM (run on the Mac), Step B — Install Docker Engine inside the VM (+7 more)

### Community 35 - "Stages (CRISP-DM phase in brackets)"
Cohesion: 0.15
Nodes (12): Divergence — roadmap from sandbox to submission (written 2026-10-19), End goal, If you're short on time, cut in this order, Key point: the sandbox is on the critical path now, Stage 1 — Finish the sandbox *(Data Understanding)*, Stage 2 — Generate traces *(Data Understanding → Preparation)*, Stage 3 — Prepare the data *(Data Preparation)*, Stage 4 — Build the model step by step *(Modelling)* (+4 more)

### Community 36 - "instructions_for_record.md"
Cohesion: 0.40
Nodes (4): 1. Real internet is unreachable → should fail or time out, 2. Any domain resolves to INetSim → should return INetSim's fake page, 3. The proxy adds the key → should return JSON about your key, not a 401 error, 4. Every other path is blocked → should return 403

## Knowledge Gaps
- **56 isolated node(s):** `graphify`, `What Changed From v7.0 (read this first)`, `The precedent this design follows`, `The integration flow (v8)`, `What this is, precisely — and what it is not` (+51 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Tiny standalone demo of the CORE IDEA behind Divergence: turn text into numbers`, `Experiment 7 live demo pipeline (Phase 2).  Runs a skill inside the OpenClaw/AGT`, `Baseline: AGT-only (non-trained). Build order item 11.  Decision from AGT's own` to the rest of the system?**
  _98 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SkillSample` be split into smaller, more focused modules?**
  _Cohesion score 0.14210526315789473 - nodes in this community are weakly interconnected._
- **Should `DIVERGENCE v8` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `Divergence — Architecture & Build Plan` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `setup_notes.md` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._