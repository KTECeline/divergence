# Graph Report - Divergence  (2026-10-25)

## Corpus Check
- 3010 files · ~273,448,399 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 470 nodes · 693 edges · 55 communities (32 shown, 23 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b49a2040`
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
- [[_COMMUNITY_diagnose.py|diagnose.py]]
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
- [[_COMMUNITY_batch_run.py|batch_run.py]]
- [[_COMMUNITY_pilot_run.py|pilot_run.py]]
- [[_COMMUNITY_comparison|comparison.md]]
- [[_COMMUNITY_test_outcome.py|test_outcome.py]]
- [[_COMMUNITY_Synthetic user a fake person living in the sandbox|Synthetic user: a fake person living in the sandbox]]
- [[_COMMUNITY_notes|notes.md]]
- [[_COMMUNITY_MEMORY|MEMORY.md]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_USER|USER.md]]
- [[_COMMUNITY_Direct-execution mode (Stage 3, second execution mode)|Direct-execution mode (Stage 3, second execution mode)]]
- [[_COMMUNITY_run_direct.py|run_direct.py]]
- [[_COMMUNITY_entrypoint_direct.sh|entrypoint_direct.sh]]
- [[_COMMUNITY_Encoder|Encoder]]
- [[_COMMUNITY_Instructed-agent mode (Stage 3, third execution mode)|Instructed-agent mode (Stage 3, third execution mode)]]
- [[_COMMUNITY_run_instructed.py|run_instructed.py]]
- [[_COMMUNITY_Encoder|Encoder]]

## God Nodes (most connected - your core abstractions)
1. `SkillSample` - 26 edges
2. `normalise()` - 23 edges
3. `Sandbox build log` - 19 edges
4. `load_samples()` - 15 edges
5. `signals()` - 15 edges
6. `parse_skill_md()` - 13 edges
7. `attribution_coverage()` - 13 edges
8. `trace_to_enriched_text()` - 13 edges
9. `ev()` - 13 edges
10. `provisional_outcome()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `test_group_keys_tie_variants_together()` --calls--> `group_key()`  [EXTRACTED]
  tests/test_loader.py → src/data/loader.py
- `test_missing_opening_dashes()` --calls--> `split_frontmatter()`  [EXTRACTED]
  tests/test_loader.py → src/data/loader.py
- `test_generator_marker_stripped()` --calls--> `parse_skill_md()`  [EXTRACTED]
  tests/test_loader.py → src/data/loader.py
- `test_horizontal_rule_is_not_frontmatter()` --calls--> `parse_skill_md()`  [EXTRACTED]
  tests/test_loader.py → src/data/loader.py
- `test_normal_frontmatter()` --calls--> `parse_skill_md()`  [EXTRACTED]
  tests/test_loader.py → src/data/loader.py

## Import Cycles
- None detected.

## Communities (55 total, 23 thin omitted)

### Community 0 - "SkillSample"
Cohesion: 0.12
Nodes (27): build_disclosed_payload_set(), build_proxy_labelling_sheet(), build_swapped_description_set(), Build the control sets that separate inconsistency from maliciousness.  Used by, Sample n malicious skills into a CSV for hand-labelling.      Columns: sample_id, Benign trace paired with a different benign skill's description.      Inconsiste, Malicious trace paired with a description that honestly states the payload., save_instructed_samples() (+19 more)

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
Cohesion: 0.12
Nodes (34): _area(), _describe_exec(), _endpoint_words(), _host(), _in_skill(), _Phrase, _phrases(), _program() (+26 more)

### Community 8 - "Citation notes (drafted, not yet placed in the report)"
Cohesion: 0.50
Nodes (3): Citation notes (drafted, not yet placed in the report), ClawHub Security Signals — motivating evidence (not used as data), Phase 1 trace capture — OpenCode-as-agent-proxy (methodology/scope note)

### Community 9 - "similarity.py"
Cohesion: 0.27
Nodes (9): consistency_score(), consistency_scores(), ndarray, Cosine similarity scoring between description and enriched-trace vectors (pipeli, cosine_similarity(Vector_A, Vector_B) -> score in [0, 1]., Row-wise consistency_score for two (n, d) arrays of paired vectors., Unit tests for the cosine consistency score (pipeline Step 4)., test_batch_matches_single() (+1 more)

### Community 25 - "setup_notes.md"
Cohesion: 0.10
Nodes (20): Environment (recorded 2026-10-19), Isolation checks (2026-10-19), LLM choice for the agent (OpenCode) — researched 2026-10-19, Pending, Phase 2 — OpenClaw/AGT sandbox setup notes, Sandbox build log, Step A — Copy MalSkillBench into the VM (run on the Mac), Step B — Install Docker Engine inside the VM (+12 more)

### Community 35 - "Stages (CRISP-DM phase in brackets)"
Cohesion: 0.15
Nodes (12): Divergence — roadmap from sandbox to submission (written 2026-10-19), End goal, If you're short on time, cut in this order, Key point: the sandbox is on the critical path now, Stage 1 — Finish the sandbox *(Data Understanding)*, Stage 2 — Generate traces *(Data Understanding → Preparation)*, Stage 3 — Prepare the data *(Data Preparation)*, Stage 4 — Build the model step by step *(Modelling)* (+4 more)

### Community 36 - "instructions_for_record.md"
Cohesion: 0.40
Nodes (4): 1. Real internet is unreachable → should fail or time out, 2. Any domain resolves to INetSim → should return INetSim's fake page, 3. The proxy adds the key → should return JSON about your key, not a 401 error, 4. Every other path is blocked → should return 403

### Community 37 - "batch_run.py"
Cohesion: 0.11
Nodes (22): Counter, load_runs(), main(), Agent-model comparison for the trace-generation pilot (report Ch. 4.2).  Inputs, build_sample(), classify_outcome(), group_key(), main() (+14 more)

### Community 38 - "pilot_run.py"
Cohesion: 0.09
Nodes (42): attribution_coverage(), _bash_roots(), _direct_actions(), _is_noise_read(), _is_noise_write(), _match_bash_calls(), normalise(), _open_mode() (+34 more)

### Community 42 - "test_outcome.py"
Cohesion: 0.09
Nodes (46): build_samples(), build_direct_samples(), Build one SkillSample per direct-execution run -> samples_direct.jsonl.  Direct, save_direct_samples(), _split_map(), first_paragraph(), group_key(), build_instructed_samples() (+38 more)

### Community 43 - "Synthetic user: a fake person living in the sandbox"
Cohesion: 0.33
Nodes (5): Steps (you run these; the VM commands go inside `limactl shell dvg-lab`), Synthetic user: a fake person living in the sandbox, What gets compared, What this is, Why it's a separate pilot, not a rerun

### Community 47 - "README.md"
Cohesion: 0.20
Nodes (9): Direct-execution review (second slice), How to decide, in order, How to do it, Outcome review: how to label the runs, Priorities, The labels, Type-A recheck (fourth slice), What each row shows (+1 more)

### Community 50 - "Direct-execution mode (Stage 3, second execution mode)"
Cohesion: 0.22
Nodes (8): Containment (unchanged from the agent sandbox), Direct-execution mode (Stage 3, second execution mode), Files, Full run (a few hours, free, resumable — do it overnight), Id lists, Rules (so the result survives a viva), Run (inside the VM), Why

### Community 51 - "run_direct.py"
Cohesion: 0.50
Nodes (4): main(), Path, Stage 3 direct-execution runner.  Runs each listed skill's OWN scripts directly, read_ids()

### Community 53 - "Encoder"
Cohesion: 0.10
Nodes (27): Central configuration: paths, model names, thresholds, seeds.  Every module read, load_samples(), build_dataset(), load_labelled_dataset(), Merge the hand reviews into ONE labelled dataset for modelling.  Each execution, Rows of labelled_dataset.jsonl, optionally only those in the given splits., _read(), final_text() (+19 more)

### Community 54 - "Instructed-agent mode (Stage 3, third execution mode)"
Cohesion: 0.29
Nodes (6): After transfer, Containment, Instructed-agent mode (Stage 3, third execution mode), Model, Steps (in the VM), Why

### Community 55 - "run_instructed.py"
Cohesion: 0.43
Nodes (6): main(), Path, Stage 3 instructed-agent runner (third execution mode).  Some malicious skills c, Reuse batch_run's spend reader if present; else return -1 (no cap)., read_ids(), read_spend_usd()

### Community 56 - "Encoder"
Cohesion: 0.18
Nodes (6): Encoder, ndarray, Sentence-BERT load + encode wrapper (pipeline Steps 1 and 3).  Build order item, Thin wrapper around a sentence-transformers model.      Loads either the pretrai, Longer inputs are truncated by the model, so later text is unseen., One unit-length vector per text, so a dot product is the cosine.

## Knowledge Gaps
- **90 isolated node(s):** `entrypoint_direct.sh script`, `graphify`, `What Changed From v7.0 (read this first)`, `The precedent this design follows`, `The integration flow (v8)` (+85 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_dataset()` connect `Encoder` to `batch_run.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `SkillSample` connect `SkillSample` to `test_outcome.py`, `Encoder`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `load_samples()` connect `Encoder` to `SkillSample`, `test_outcome.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **What connects `Tiny standalone demo of the CORE IDEA behind Divergence: turn text into numbers`, `Agent-model comparison for the trace-generation pilot (report Ch. 4.2).  Inputs`, `Experiment 7 live demo pipeline (Phase 2).  Runs a skill inside the OpenClaw/AGT` to the rest of the system?**
  _195 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SkillSample` be split into smaller, more focused modules?**
  _Cohesion score 0.12298387096774194 - nodes in this community are weakly interconnected._
- **Should `DIVERGENCE v8` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `Divergence — Architecture & Build Plan` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._