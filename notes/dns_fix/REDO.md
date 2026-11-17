# DNS fix: full redo, step by step

Run everything from the repo root (`cd ~/Desktop/Projects/School/Divergence`). Each step
depends on the one before it; do not reorder. Steps marked **(Claude)** are code changes:
ask Claude to do them.

## 0. Back up (results and models are git-ignored, so git cannot restore them)

```bash
B=../divergence_before_dns_fix && mkdir -p $B
cp -R results models $B/
cp -R data/processed $B/processed
```

## 1. Apply the fix (Claude) — DONE 2026-11-17

Say "apply the DNS fix". Claude changes `divergence/preprocessing/normalise_trace.py`
(`_os_events` also reads DNS names from the sandbox resolver's replies) and adds tests. Then:

```bash
.venv/bin/python -m pytest -q
```

## 2. Rebuild the dataset traces — DONE 2026-11-17 (check_dataset OK; only `trace` changed, 170 runs, +305 dns_lookup)

```bash
.venv/bin/python -m divergence.data.loader              # agent runs      -> samples.jsonl
.venv/bin/python -m divergence.data.loader_direct       # direct runs     -> samples_direct.jsonl
.venv/bin/python -m divergence.data.loader_instructed   # instructed runs -> samples_instructed.jsonl
.venv/bin/python -m divergence.labelling.merge_labels   # -> labelled_dataset.jsonl
.venv/bin/python notes/dns_fix/check_dataset.py         # must end with OK
```

**Do not run `divergence.data.splitter`.** The split is frozen in `split_assignment.csv`;
re-running it would reshuffle the train/test split.

`check_dataset.py` must still show 308 runs, POS 149, NEG 159, the same split counts, and
0 parity failures. The labels come from the hand review, so they must not move.

## 3. Retrain (notebooks, in order)

One full command per line: zsh does not split a multi-word shell variable, so a shortcut
variable for the command fails. `caffeinate -i` keeps the Mac awake; keep it plugged in.

```bash
caffeinate -i .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/02_baseline_pretrained.ipynb
caffeinate -i .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/03_trace_to_text_enriched.ipynb
caffeinate -i .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/04_structural_flags.ipynb
caffeinate -i .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/05_setfit_finetune.ipynb       # retrains the encoder -> models/finetuned_embedding/
caffeinate -i .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/06_calibration.ipynb           # refits the calibrator -> models/calibration_model.json
```

## 4. Rerun the experiments

LLM-judge caches are keyed by run, not by trace, so the old answers would be reused for the
new traces. Move them aside first:

```bash
mkdir -p results/archive/before_dns_fix
mv results/llm_judge results/archive/before_dns_fix/llm_judge
mv data/processed/controls/disclosed_descriptions.jsonl results/archive/before_dns_fix/
ollama pull llama3.2:3b                       # the third judge model is no longer installed
```

Make sure Ollama is running (the Ollama app, or `ollama serve` in another terminal). Then:

```bash
.venv/bin/python -m divergence.experiments.exp1_baseline_comparison
.venv/bin/python -m divergence.experiments.exp1b_skill_level
.venv/bin/python -m divergence.experiments.exp1c_llm_judge --model qwen2.5:7b --model llama3.1:8b --model llama3.2:3b
.venv/bin/python -m divergence.experiments.exp1d_capability_overlap
.venv/bin/python -m divergence.experiments.exp1e_paired_tests
.venv/bin/python -m divergence.experiments.exp1f_threshold_curve
.venv/bin/python -m divergence.experiments.exp2_ablation
.venv/bin/python -m divergence.experiments.exp2b_finetune_ablation
.venv/bin/python -m divergence.experiments.exp3_attack_type_breakdown
.venv/bin/python -m divergence.experiments.exp4_embedding_model_comparison            # if it cannot download a model: prefix HF_HUB_OFFLINE=0
.venv/bin/python -m divergence.experiments.exp5_control_experiments                   # regenerates the disclosed descriptions with Ollama
.venv/bin/python -m divergence.experiments.exp5a_proxy_validity
.venv/bin/python -m divergence.experiments.exp6_holdout_generalisation
caffeinate -i .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/07_results_analysis.ipynb      # figures
```

`proxy_labelling_sheet_labelled.csv` (the 5a hand labels) stays: it labels the skills'
descriptions, which do not change.

## 5. Check the fix on a live trial

```bash
.venv/bin/python -m pytest -q
.venv/bin/divergence install --skill-dir notes/dns_fix/urllib-skill
```

Before the fix this skill (uploads `~/.aws/credentials` from Python with `urllib`) was ALLOWED
at 27%. After it, the direct run should name `collect.evil-c2.example` and FLAG.

Then compare old and new numbers:

```bash
diff <(cut -d, -f1-6 ../divergence_before_dns_fix/results/exp1_results.csv) <(cut -d, -f1-6 results/exp1_results.csv)
```

## 6. Release the new model (you)

```bash
H=release/hf_bundle && rm -rf $H && mkdir -p $H
rsync -a --exclude README.md --exclude 2_Normalize models/finetuned_embedding/ $H/
cp models/calibration_model.json $H/
cp release/hf_model_card.md $H/README.md      # update its numbers first
.venv/bin/hf upload KTECeline/divergence-minilm-l6 $H . --commit-message "v0.2.0: retrained after DNS capture fix"
```

Give Claude the new commit hash: it moves the pin in `divergence/model_store.py`, bumps the
version, and checks a fresh download from an empty cache gives the same verdicts as `models/`.
Never upload `models/finetuned_embedding/README.md`: the auto-generated card contains
MalSkillBench training samples.

## 7. Update the write-up

Every number in the report, README, model card and `notes/` that came from `results/` changes.
State the fix in the methodology: "DNS names are read from the resolver's replies as well as
from command arguments; this recovered 17 hosts the upstream runner missed".
