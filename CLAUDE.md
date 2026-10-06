## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

# DIVERGENCE v8
> *Intent–Behaviour Consistency Scoring for Autonomous AI Agent Skills — AGT-Integrated Evaluator*
 
**Version:** 8.0 — Plugin requirement formalised, AGT technical details verified, methodology finalised as CRISP-DM only (July 2026)
 
---
 
## What Changed From v7.0 (read this first)
 
| Change | Why |
|---|---|
| **Deployment upgraded from a demonstration script/log output to a registered AGT evaluator (`DivergenceEvaluator`)**, following the documented precedent of AGT's own `PromptDefenseEvaluator`. | Supervisor confirmed a log-only demonstration is **not sufficient for an FYP** — it must be an actual plugin/evaluator integrated with AGT's architecture, not a standalone script reading AGT's output after the fact. |
| **Methodology finalised as CRISP-DM only — the Agile/hybrid framing from v7 is dropped entirely.** No "Sprint," "Iteration," or Agile terminology anywhere in the report. Incremental component-by-component development is described exactly once, inside the Modelling phase, as a description of *how* that phase was executed — not as a second named methodology. | Supervisor confirmed CRISP-DM alone is sufficient: *"anything that fits my FYP the most."* CRISP-DM's own iterative phase structure already accommodates progressive component development without needing a second framework layered on top — this is a smaller, more defensible claim, easier to hold up in a viva. |
| **AGT's actual technical architecture verified via direct research** (previously assumed/inferred). Confirmed: AGT is real, MIT-licensed, public-preview software (launched April 2026), with a Python SDK (`pip install agent-governance-toolkit[full]`). Confirmed OpenClaw is also real and documented as an AGT-adjacent framework. | Grounds every AGT-related claim in the report in verified fact rather than assumption — removes risk of an examiner discovering an unverifiable technical claim. |
| **Verdict output confirmed NOT binary.** AGT's policy engine (ACS) returns one of five decisions (ALLOW / DENY / MODIFY / STEP_UP / DEFER), and verdicts explicitly support **optional evidence fields** that propagate into telemetry. | Directly resolves the open question from v7 about whether Divergence's nuanced score would be flattened at the interface boundary. It is not — Divergence's consistency score, structural flags, and reasoning populate these evidence fields. |
| **Direct technical precedent identified: `PromptDefenseEvaluator`.** A real, shipped AGT component that runs *pre-policy* (before the Cedar policy engine's decision), returning a structured result object: `result.score`, `result.missing`, `result.compliance`. | This is the closest possible real-world precedent for Divergence's own architecture. `DivergenceEvaluator` is designed to follow the exact same shape — `result.consistency_score`, `result.structural_flags`, `result.verdict/reasoning` — evaluated pre-installation rather than pre-deployment, but structurally identical. Cite this directly in 2.4.3.4. |
| **Integration point named specifically: AGT's "Agent Marketplace — Plugin governance and trust scoring" subsystem.** | A more precise citation target than "AGT's plugin interface" generally — this is the actual named AGT component responsible for governing plugins/skills and computing trust scores, which is exactly the function Divergence performs. |
| **Dataset finalised: MalSkillBench-anchored, hybrid with supplementary OpenClaw capture.** (Carried over from the mid-v7 dataset decision, now confirmed final.) 3,944 malicious + 4,000 benign skills, runtime-verified via Docker sandbox execution, three-dimensional taxonomy (attack vector × behaviour class × insertion strategy, 108 cells). Supplemented with traces captured directly within this project's own OpenClaw/AGT sandbox. Three-way split: fine-tune / calibration / held-out test. | Replaces v7's "20–100 sample, three-tier (benchmark-anchored/simulated/real)" placeholder strategy with a named, real, citable benchmark — resolves the supervisor's "dataset is minimal" concern from the earlier meeting. |
| **Survey completed: 38 respondents**, exceeding the 30-participant guideline minimum. Functions as **design validation**, not traditional requirements-gathering — since technical design decisions were already made independently, the survey's role is to confirm those decisions align with real practitioner preferences, and to provide primary evidence that the underlying problem (skill behaviour-description mismatch) is real. | Survey status flips from "planned" to "completed and analysed" — Chapter 3 reports findings in past tense. Several findings independently corroborate design choices already present in the v7 architecture (see below). |
 
**Everything else — problem statement, scope, threat model, out-of-scope boundaries, structural red-flag rules, enriched trace-to-text conversion, embedding/fine-tuning/calibration pipeline mechanics — is unchanged from v7.0 and remains in force.**
 
---
 
## Updated Section 5 Equivalent — How Divergence Integrates With AGT (v8)
 
### The precedent this design follows
 
AGT ships at least one evaluator that runs *before* its policy engine issues a decision, contributing structured evidence rather than a binary verdict of its own:
 
```python
from agent_governance.evaluators import PromptDefenseEvaluator
evaluator = PromptDefenseEvaluator()
result = evaluator.evaluate(agent_config.system_prompt)
# result.score = 49
# result.missing = ['indirect-injection', 'role-boundary', ...]
# result.compliance = {'OWASP_LLM01': 'FAIL', 'OWASP_LLM06': 'PASS', ...}
```
 
Divergence is architected to follow this exact pattern:
 
```python
from divergence.evaluators import DivergenceEvaluator
evaluator = DivergenceEvaluator()
result = evaluator.evaluate(skill_description, agt_audit_log)
# result.consistency_score = 0.31
# result.structural_flags = ['flag_unmentioned_domain']
# result.verdict = "FLAG"
# result.reasoning = "Low semantic alignment between stated purpose and observed behaviour..."
```
 
### The integration flow (v8)
 
```
Skill submitted for installation
      |
      v
Skill executed within AGT's isolated execution sandbox (privilege rings)
      |
      v
AGT captures the full action sequence as a Merkle-chained audit log
      |
      v
DivergenceEvaluator.evaluate(skill_description, audit_log) is called,
following AGT's pre-policy evaluator pattern (same shape as PromptDefenseEvaluator)
      |
      v
Divergence's internal pipeline runs (unchanged from v7):
  Sentence-BERT encoding -> enriched trace-to-text -> cosine similarity
  -> structural red-flag rules -> SetFit-fine-tuned embedding comparison
  -> logistic regression calibration -> final result object
      |
      v
result object (score, flags, reasoning) attached as evidence to AGT's
verdict schema, surfaced to the user BEFORE real installation proceeds
      |
      v
User sees: AGT's own policy decision (ALLOW/DENY/MODIFY/STEP_UP/DEFER)
           + Divergence's consistency score, flags, and explanation
```
 
### What this is, precisely — and what it is not
Divergence is implemented as a custom evaluator following AGT's own documented extension pattern, run within this project's own AGT/OpenClaw sandbox instance. It is **not** a claim of being merged into Microsoft's official AGT distribution or its production Agent Marketplace — that distinction matters and should be stated plainly in the report (2.4.3.4, 3.2.3.6) to avoid overclaiming. The precedent this design follows (`PromptDefenseEvaluator`) is itself real and shipped; Divergence is a new evaluator built to the same architectural contract, not a modification of AGT's own source.
 
### Technical grounding (for 2.4.3.4)
- AGT: MIT-licensed, public-preview, launched April 2026, Python SDK via `pip install agent-governance-toolkit[full]`
- Five governance decisions: ALLOW, DENY, MODIFY, STEP_UP, DEFER
- Verdicts carry optional evidence fields, propagated to telemetry — this is where Divergence's output lives
- Precedent evaluator: `PromptDefenseEvaluator`, running pre-policy, returning `.score`/`.missing`/`.compliance`
- Named integration subsystem: "Agent Marketplace — Plugin governance and trust scoring"
- **Version stability caveat carried forward from v7's constraint:** AGT is actively evolving; package names have already been renamed mid-2026 (e.g. `agent-os-kernel` → `agent-governance-toolkit-core`). The exact AGT version used must be pinned and recorded.
 
---
 
## Updated Methodology Statement (v8)
 
**CRISP-DM is the sole named methodology.** No hybrid, no Agile, no Scrum terminology anywhere in the report. The six phases (Business Understanding, Data Understanding, Data Preparation, Modelling, Evaluation, Deployment) structure Chapter 3 directly (3.2.3.1–3.2.3.6). Incremental, component-by-component construction — pretrained-only pipeline first, then structural flags, then SetFit fine-tuning, then calibration, each validated before the next was added — is described exactly once, inside the Modelling phase, framed as an expression of CRISP-DM's own iterative design rather than a separate methodology.
 
The Deployment phase's deliverable is now the working `DivergenceEvaluator`, not a demonstration log.
 
---
 
## Updated Dataset Statement (v8)
 
**Primary/anchor dataset:** MalSkillBench (Guo et al., 2026)
- 3,944 malicious + 4,000 benign agent skills
- Runtime-verified: malicious samples confirmed via Docker sandbox execution (syscall trace + LLM-judge verification) before inclusion
- Three-dimensional taxonomy: attack vector (Code Injection / Prompt Injection / Mixed) × behaviour class × insertion strategy — 108 labelled cells
- Construction: closed-loop generate-verify-feedback (3,214 samples) + wild-collected and manually verified (703 samples) + tool-bundled samples
- License: academic research use
 
**Supplementary dataset:** skill execution traces captured directly within this project's own OpenClaw/AGT sandbox, to confirm the detection approach transfers to the specific target platform (MalSkillBench was constructed around agent skills generally, not OpenClaw specifically).
 
**Split:** fine-tuning split, calibration split, held-out test split — strictly separated to prevent leakage, per v7's original anti-leakage design (unchanged).
 
**Known limitation, stated explicitly rather than hidden:** MalSkillBench's own wild-collected subset shows attack-category skew (86.3% concentrated on dependency-impersonation attacks, prompt injection nearly absent in that subset) — this is why the hybrid strategy (benchmark anchor + local supplementary capture) was adopted rather than relying on wild-collected samples alone.
 
---
 
## Updated Survey Statement (v8)
 
**Status: complete.** 38 respondents via Google Forms, exceeding the 30-participant minimum. Purposive/convenience sampling, targeting current/prospective users of autonomous agent frameworks (AI/ML developers, software engineers, IT students, general end users).
 
**Stated limitation:** the sample did not reach dedicated security researchers or marketplace-maintainer-type respondents specifically, despite these being named target users in Section 1.5.3. Acknowledged as a scope limitation of the validation exercise, not of the technical system.
 
**Key findings (full write-up in 3.4):**
1. Problem is empirically real — 44.7% of respondents (17/38) directly encountered a skill behaving inconsistently with its description
2. Existing tools perceived as structurally inadequate — independently corroborates the exact three limitations argued in Chapter 2's literature review (runtime-only behaviour, natural-language-triggered actions, speed)
3. Strong demand for the proposed system — 33/38 (86.8%) rated usefulness 4-5 [verified against the Google Forms chart embedded as Figure 43 in the IR report: 18 rated 4 (47.4%) + 15 rated 5 (39.5%)]
4. Strong preference for explainability/granularity over binary verdicts — validates the `result.consistency_score`/`.structural_flags`/`.reasoning` output design already present in the v7/v8 architecture
5. Deployment timing preference roughly evenly split (automatic / on-demand / both)
6. Concern ranking maps closely onto the implemented structural red-flag categories (`flag_unmentioned_domain`, `flag_credential_access`, `flag_undeclared_action_type`)
7. Baseline trust in skill descriptions is moderate (3.05/5 average), supporting the premise that verification adds value without requiring an assumption of total ecosystem distrust
 
---
 
## Reference Library Additions (v8)
 
### AGT technical sources (new)
- microsoft/agent-governance-toolkit (GitHub repository, README, QUICKSTART.md, docs/)
- Introducing the Agent Governance Toolkit: Open-source runtime security for AI agents. Microsoft Open Source Blog (2026, April).
- Agent Control Specification (ACS) documentation — microsoft.github.io/agent-governance-toolkit
 
### Methodology sources (new, from Chapter 3 restructure)
- Chapman, P., et al. (2000). CRISP-DM 1.0: Step-by-step data mining guide.
- Fayyad, U., Piatetsky-Shapiro, G., & Smyth, P. (1996). From data mining to knowledge discovery in databases.
- SEMMA methodology — SAS Institute documentation.
- Team Data Science Process (TDSP) — Microsoft documentation.
- Balaji, S., & Murugaiyan, M. S. (2012). Waterfall vs. V-model vs. Agile: A comparative study on SDLC. (already in v7 library)
 
### Chapter 2 additions confirmed still needed (from earlier session, unchanged)
- Devlin, J., et al. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding.
- Vaswani, A., et al. (2017). Attention is all you need.
- Foundational STS/NLI sources (STS Benchmark, SNLI) — for 2.2.12
 
**Note:** author details for several sources above should be verified directly from their original pages before finalising the reference list, consistent with the verification practice already established for v7's library.
 
---
 
## What Was NOT Changed From v7
- Core detection pipeline: pretrained Sentence-BERT → enriched trace-to-text → cosine similarity → structural red-flag rules → SetFit few-shot fine-tuning → logistic regression calibration
- Threat model and scope boundaries (observable action-trace deviation only; payload-less and install-time attacks remain out of scope)
- Evaluation design: AGT-only, behaviour-only, text-only, LLM-as-judge, pretrained-only baselines; ablation studies; McNemar's test
- Tech stack: Python, sentence-transformers, SetFit, scikit-learn, Docker
 
---
 
*DIVERGENCE v8.0 — CRISP-DM methodology, AGT-integrated evaluator plugin, MalSkillBench-anchored hybrid dataset, completed 38-respondent validation survey — July 2026*