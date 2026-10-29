# Graph Report - Divergence  (2026-10-29)

## Corpus Check
- 3041 files · ~273,600,852 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 748 nodes · 1454 edges · 53 communities (41 shown, 12 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2db71a69`
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
- [[_COMMUNITY_Encoder|Encoder]]
- [[_COMMUNITY_LogisticCalibrator|LogisticCalibrator]]
- [[_COMMUNITY_exp1_baseline_comparison.py|exp1_baseline_comparison.py]]
- [[_COMMUNITY_exp3_attack_type_breakdown.py|exp3_attack_type_breakdown.py]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_00_toy_demo.py|00_toy_demo.py]]
- [[_COMMUNITY_setup_notes|setup_notes.md]]
- [[_COMMUNITY_smoke_test.py|smoke_test.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
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
- [[_COMMUNITY_load_samples|load_samples]]
- [[_COMMUNITY_Instructed-agent mode (Stage 3, third execution mode)|Instructed-agent mode (Stage 3, third execution mode)]]
- [[_COMMUNITY_run_instructed.py|run_instructed.py]]
- [[_COMMUNITY_SkillAssessment|SkillAssessment]]
- [[_COMMUNITY_DivergenceResult|DivergenceResult]]

## God Nodes (most connected - your core abstractions)
1. `compute_structural_flags()` - 35 edges
2. `normalise()` - 24 edges
3. `LogisticCalibrator` - 23 edges
4. `SkillSample` - 22 edges
5. `DivergenceEvaluator` - 22 edges
6. `trace_to_enriched_text()` - 20 edges
7. `point_metrics()` - 19 edges
8. `Sandbox build log` - 19 edges
9. `load_labelled_dataset()` - 18 edges
10. `mcnemar_test()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `FakeEncoder` --uses--> `LogisticCalibrator`  [INFERRED]
  tests/test_evaluator.py → src/calibration/logistic_calibrator.py
- `test_mcnemar_counts_disagreements()` --calls--> `mcnemar_test()`  [EXTRACTED]
  tests/test_evaluator.py → src/evaluation/metrics.py
- `FakeEncoder` --uses--> `DivergenceResult`  [INFERRED]
  tests/test_evaluator.py → src/evaluator/divergence_evaluator.py
- `main()` --calls--> `parse_skill_md()`  [EXTRACTED]
  sandbox/demo_pipeline.py → src/data/loader.py
- `test_format_trace_collapses_repeats_and_caps_length()` --calls--> `format_trace()`  [EXTRACTED]
  tests/test_llm_judge.py → src/baselines/llm_as_judge.py

## Import Cycles
- None detected.

## Communities (53 total, 12 thin omitted)

### Community 0 - "SkillSample"
Cohesion: 0.11
Nodes (31): predict(), Baseline: behaviour-only (non-trained). Build order item 11.  Uses the observed, How many of the three rules fire on the behaviour alone (0-3); used for ranking., score(), declared(), observed(), predict(), Baseline: capability overlap (non-trained, no embedding).  Turns both sides into (+23 more)

### Community 1 - "DIVERGENCE v8"
Cohesion: 0.12
Nodes (16): AGT technical sources (new), Chapter 2 additions confirmed still needed (from earlier session, unchanged), DIVERGENCE v8, graphify, Methodology sources (new, from Chapter 3 restructure), Reference Library Additions (v8), Technical grounding (for 2.4.3.4), The integration flow (v8) (+8 more)

### Community 2 - "Divergence — Architecture & Build Plan"
Cohesion: 0.12
Nodes (15): Dataset, Divergence, Methodology, Project layout, Setup, 1. One-sentence description, 2. Current phase, 3. Project directory structure (+7 more)

### Community 3 - "StructuralFlags"
Cohesion: 0.11
Nodes (37): flat_masked_text(), Flat text without the sandbox artefacts: connections to the sinkhole IP (the DNS, _area(), _describe_exec(), _endpoint_words(), _host(), _in_skill(), _Phrase (+29 more)

### Community 4 - "divergence_evaluator.py"
Cohesion: 0.06
Nodes (58): ndarray, Baseline: text-only. Build order item 11.  Uses the declared skill description a, TextOnlyBaseline, Central configuration: paths, model names, thresholds, seeds.  Every module read, load_labelled_dataset(), Merge the hand reviews into ONE labelled dataset for modelling.  Each execution, Rows of labelled_dataset.jsonl, optionally only those in the given splits., Sentence-BERT load + encode wrapper (pipeline Steps 1 and 3).  Build order item (+50 more)

### Community 5 - "LogisticCalibrator"
Cohesion: 0.07
Nodes (27): All Hyperparameters, Bias, Risks and Limitations, BibTeX, Citation, Direct Usage (Sentence Transformers), Direct Usage (Transformers), Downstream Usage (Sentence Transformers), Framework Versions (+19 more)

### Community 6 - "trace_to_enriched_text"
Cohesion: 0.19
Nodes (12): _as_dict(), from_agt_audit_log(), is_divergence_trace(), Turn an AGT audit log into the action list the Divergence pipeline reads.  AGT 4, An AuditEntry (pydantic model) or an already-dumped dict., True when the log is already in Divergence's normalised format., AGT audit entries (+ the sandbox's OS events) -> Divergence action list.      os, Accept either format: a normalised Divergence trace passes through unchanged. (+4 more)

### Community 8 - "Citation notes (drafted, not yet placed in the report)"
Cohesion: 0.50
Nodes (3): Citation notes (drafted, not yet placed in the report), ClawHub Security Signals — motivating evidence (not used as data), Phase 1 trace capture — OpenCode-as-agent-proxy (methodology/scope note)

### Community 9 - "similarity.py"
Cohesion: 0.27
Nodes (9): consistency_score(), consistency_scores(), ndarray, Cosine similarity scoring between description and enriched-trace vectors (pipeli, cosine_similarity(Vector_A, Vector_B) -> score in [0, 1]., Row-wise consistency_score for two (n, d) arrays of paired vectors., Unit tests for the cosine consistency score (pipeline Step 4)., test_batch_matches_single() (+1 more)

### Community 10 - "demo_pipeline.py"
Cohesion: 0.20
Nodes (4): LogisticCalibrator, ndarray, Probability that each skill run is suspicious (inconsistent)., Learned weight per feature (log-odds per unit); negative = pushes towards ALLOW.

### Community 11 - "agt_only.py"
Cohesion: 0.18
Nodes (13): feature_row(), Logistic regression calibration layer (pipeline Step 6).  Build order item 9. Fi, DivergenceEvaluator — the AGT-pattern evaluator wrapping the full pipeline.  Bui, Plain-language explanation built from the same numbers that made the verdict., _reasoning(), Names of the flags that fired, for the evaluator's result object., StructuralFlags, fitted() (+5 more)

### Community 13 - "llm_as_judge.py"
Cohesion: 0.09
Nodes (36): format_trace(), LLMJudge, parse(), predict(), Path, Baseline: LLM-as-judge (non-trained). Build order item 11.  A local LLM (Ollama,, 0/1 verdict for one labelled-dataset row., One line per action; repeated identical lines collapsed; capped at MAX_LINES. (+28 more)

### Community 14 - "Encoder"
Cohesion: 0.22
Nodes (5): Encoder, ndarray, Thin wrapper around a sentence-transformers model.      Loads either the pretrai, Longer inputs are truncated by the model, so later text is unseen., One unit-length vector per text, so a dot product is the cosine.

### Community 15 - "LogisticCalibrator"
Cohesion: 0.22
Nodes (13): DivergenceEvaluator, Wraps pipeline Steps 1-6: encode description, enrich + encode trace,     cosine, calibrator(), evaluator(), FakeEncoder, Unit tests for the AGT adapter, DivergenceEvaluator (build order item 10) and th, Same vector for every text -> consistency score 1.0., test_agt_evidence_and_json() (+5 more)

### Community 16 - "exp1_baseline_comparison.py"
Cohesion: 0.38
Nodes (6): predict(), Baseline: AGT-only (non-trained). Build order item 11.  Decision from AGT's own, score(), agt_visible(), Only the tool-call layer: what AGT's own audit log would contain., test_os_events_attach_after_their_entry()

### Community 19 - "exp3_attack_type_breakdown.py"
Cohesion: 0.10
Nodes (34): Dataset, cv_auc(), finetune(), pair_dataset(), SentenceTransformer, SetFit few-shot contrastive fine-tuning of the embedding model (Step 0).  Build, Fine-tune a fresh copy of the base encoder; returns it and the logged loss per s, Mean held-out-fold AUC inside the given rows, folds grouped by skill so variants (+26 more)

### Community 25 - "setup_notes.md"
Cohesion: 0.09
Nodes (21): AGT check (2026-10-26) — what AGT 4.1.0 actually provides, Environment (recorded 2026-10-19), Isolation checks (2026-10-19), LLM choice for the agent (OpenCode) — researched 2026-10-19, Pending, Phase 2 — OpenClaw/AGT sandbox setup notes, Sandbox build log, Step A — Copy MalSkillBench into the VM (run on the Mac) (+13 more)

### Community 35 - "Stages (CRISP-DM phase in brackets)"
Cohesion: 0.15
Nodes (12): Divergence — roadmap from sandbox to submission (written 2026-10-19), End goal, If you're short on time, cut in this order, Key point: the sandbox is on the critical path now, Stage 1 — Finish the sandbox *(Data Understanding)*, Stage 2 — Generate traces *(Data Understanding → Preparation)*, Stage 3 — Prepare the data *(Data Preparation)*, Stage 4 — Build the model step by step *(Modelling)* (+4 more)

### Community 36 - "instructions_for_record.md"
Cohesion: 0.40
Nodes (4): 1. Real internet is unreachable → should fail or time out, 2. Any domain resolves to INetSim → should return INetSim's fake page, 3. The proxy adds the key → should return JSON about your key, not a 401 error, 4. Every other path is blocked → should return 403

### Community 37 - "batch_run.py"
Cohesion: 0.10
Nodes (24): Counter, load_runs(), main(), Agent-model comparison for the trace-generation pilot (report Ch. 4.2).  Inputs, build_dataset(), _read(), build_sample(), classify_outcome() (+16 more)

### Community 38 - "pilot_run.py"
Cohesion: 0.08
Nodes (45): _bash_roots(), call_effects(), _direct_actions(), _is_noise_read(), _is_noise_write(), _match_bash_calls(), normalise(), _open_mode() (+37 more)

### Community 42 - "test_outcome.py"
Cohesion: 0.06
Nodes (68): build_samples(), build_direct_samples(), Build one SkillSample per direct-execution run -> samples_direct.jsonl.  Direct, save_direct_samples(), _split_map(), first_paragraph(), group_key(), build_instructed_samples() (+60 more)

### Community 43 - "Synthetic user: a fake person living in the sandbox"
Cohesion: 0.33
Nodes (5): Steps (you run these; the VM commands go inside `limactl shell dvg-lab`), Synthetic user: a fake person living in the sandbox, What gets compared, What this is, Why it's a separate pilot, not a rerun

### Community 47 - "README.md"
Cohesion: 0.18
Nodes (10): Direct-execution review (second slice), Exp 5a disclosure review (fifth slice), How to decide, in order, How to do it, Outcome review: how to label the runs, Priorities, The labels, Type-A recheck (fourth slice) (+2 more)

### Community 50 - "Direct-execution mode (Stage 3, second execution mode)"
Cohesion: 0.22
Nodes (8): Containment (unchanged from the agent sandbox), Direct-execution mode (Stage 3, second execution mode), Files, Full run (a few hours, free, resumable — do it overnight), Id lists, Rules (so the result survives a viva), Run (inside the VM), Why

### Community 51 - "run_direct.py"
Cohesion: 0.50
Nodes (4): main(), Path, Stage 3 direct-execution runner.  Runs each listed skill's OWN scripts directly, read_ids()

### Community 53 - "load_samples"
Cohesion: 0.12
Nodes (23): load_samples(), final_text(), build_sheet(), _actions_text(), build_sheet(), Build the DIRECT-mode review slice: validate the rule-flagged payloads.  Direct, The skill's own actions, in order, as the reviewer sees them., _row() (+15 more)

### Community 54 - "Instructed-agent mode (Stage 3, third execution mode)"
Cohesion: 0.29
Nodes (6): After transfer, Containment, Instructed-agent mode (Stage 3, third execution mode), Model, Steps (in the VM), Why

### Community 55 - "run_instructed.py"
Cohesion: 0.43
Nodes (6): main(), Path, Stage 3 instructed-agent runner (third execution mode).  Some malicious skills c, Reuse batch_run's spend reader if present; else return -1 (no cap)., read_ids(), read_spend_usd()

### Community 57 - "SkillAssessment"
Cohesion: 0.07
Nodes (32): MarketplaceError, PluginInstaller, main(), plugin_name(), AuditLog, Path, Experiment 7 live demo: Divergence as a pre-install check inside AGT's marketpla, TrialRuns for every mode that has a captured result, after the parity check. (+24 more)

### Community 59 - "DivergenceResult"
Cohesion: 0.21
Nodes (7): DivergenceResult, Score one skill run.          audit_log: AGT AuditEntry objects/dicts, or an alr, evaluate() for many (description, audit_log[, os_events]) runs, encoding in one, Deterministic JSON (sorted keys), like PromptDefenseReport.to_json()., The result as evidence for AGT's policy decision (Divergence does not decide it), The original stub test, kept: the v8 four-field shape still constructs on its ow, test_result_object_shape()

## Knowledge Gaps
- **112 isolated node(s):** `demo_trial.sh script`, `DVG_MSB_ROOT`, `entrypoint_direct.sh script`, `graphify`, `What Changed From v7.0 (read this first)` (+107 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_dataset()` connect `batch_run.py` to `divergence_evaluator.py`, `load_samples`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `compute_structural_flags()` connect `SkillSample` to `divergence_evaluator.py`, `agt_only.py`, `llm_as_judge.py`, `exp1_baseline_comparison.py`, `exp3_attack_type_breakdown.py`, `DivergenceResult`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `LogisticCalibrator` (e.g. with `StructuralFlags` and `DivergenceEvaluator`) actually correct?**
  _`LogisticCalibrator` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `DivergenceEvaluator` (e.g. with `DivergenceEscalation` and `DivergencePluginInstaller`) actually correct?**
  _`DivergenceEvaluator` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Tiny standalone demo of the CORE IDEA behind Divergence: turn text into numbers`, `Agent-model comparison for the trace-generation pilot (report Ch. 4.2).  Inputs`, `Experiment 7 live demo: Divergence as a pre-install check inside AGT's marketpla` to the rest of the system?**
  _280 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SkillSample` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._
- **Should `DIVERGENCE v8` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._