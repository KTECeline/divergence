# Phase 2 — OpenClaw/AGT sandbox setup notes

**Do not start until Phase 1 experiments (Exp 1, 2, 2b, 3) are producing trusted results.**

Checklist (from Structure.md §7):
- [ ] Set up OpenClaw + AGT sandbox
- [ ] **Pin and record the exact AGT version** (packages have been renamed mid-2026, e.g. `agent-os-kernel` → `agent-governance-toolkit-core`)
- [ ] Capture supplementary skill traces → `data/supplementary/`
- [ ] Fold supplementary traces into hybrid dataset
- [ ] Re-run key experiments on hybrid dataset, compare to MalSkillBench-only results
- [ ] Build live demo pipeline (`demo_pipeline.py`) — Experiment 5
- [ ] Wire `DivergenceEvaluator` into AGT's pre-policy evaluator hook

Record here as you go: AGT version pinned, install commands, sandbox configuration,
trace capture procedure.
