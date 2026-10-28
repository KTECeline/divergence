"""Central configuration: paths, model names, thresholds, seeds.

Every module reads paths and hyperparameters from here — no hardcoded paths
elsewhere in src/.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_MALSKILLBENCH_DIR = DATA_DIR / "raw" / "malskillbench"
PROCESSED_DIR = DATA_DIR / "processed"
ENRICHED_TRACES_DIR = PROCESSED_DIR / "enriched_traces"
STRUCTURAL_FLAGS_DIR = PROCESSED_DIR / "structural_flags"
SPLITS_DIR = PROCESSED_DIR / "splits"
SUPPLEMENTARY_DIR = DATA_DIR / "supplementary"  # Phase 2

# MalSkillBench ships skills only; it lives under vendor/ next to its runner.
MALSKILLBENCH_DIR = PROJECT_ROOT / "vendor" / "MalSkillBench"
SKILLS_DIR = MALSKILLBENCH_DIR / "Dataset" / "Skills"
INVENTORY_PATH = SKILLS_DIR / "malware" / "_source_inventory.txt"

# Behaviour traces produced in the sealed sandbox (Stage 2, vendor/batch_run.py)
TRACES_DIR = DATA_DIR / "raw" / "traces" / "batch_out"
TRACES_SUMMARY_PATH = TRACES_DIR / "summary.csv"
SAMPLES_PATH = PROCESSED_DIR / "samples.jsonl"

# Direct-execution traces (Stage 3, sandbox/direct_exec): the skill's own
# scripts run with no agent, so payloads fire without the agent's refusal.
DIRECT_TRACES_DIR = DATA_DIR / "raw" / "traces" / "direct_out"
DIRECT_SAMPLES_PATH = PROCESSED_DIR / "samples_direct.jsonl"

# Instructed-agent traces (Stage 3, sandbox/instructed_agent): the ~361
# prose-only malicious skills re-run with a low-refusal, tool-capable model and
# a compliant sandbox-analysis prompt, so prose-instruction payloads (which only
# an agent can trigger) surface. These ARE agent runs, so the agent outcome
# rules apply; they share each skill's sample_id, hence its split.
INSTRUCTED_TRACES_DIR = DATA_DIR / "raw" / "traces" / "instructed_out"
INSTRUCTED_SAMPLES_PATH = PROCESSED_DIR / "samples_instructed.jsonl"
REVIEW_DIR = PROCESSED_DIR / "review"

MODELS_DIR = PROJECT_ROOT / "models"
FINETUNED_EMBEDDING_DIR = MODELS_DIR / "finetuned_embedding"
CALIBRATION_MODEL_PATH = MODELS_DIR / "calibration_model.json"

RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

# --- Split files -----------------------------------------------------------
FINETUNE_SPLIT_PATH = SPLITS_DIR / "finetune.jsonl"
CALIBRATION_SPLIT_PATH = SPLITS_DIR / "calibration.jsonl"
HELD_OUT_TEST_SPLIT_PATH = SPLITS_DIR / "held_out_test.jsonl"
SPLIT_ASSIGNMENT_PATH = SPLITS_DIR / "split_assignment.csv"
# Group-aware 5-fold assignment: 2 folds fine-tune, 1 calibration, 2 test (40/20/40)
SPLIT_FOLDS = {"finetune": (0, 1), "calibration": (2,), "held_out_test": (3, 4)}

# --- Models ----------------------------------------------------------------
# Pretrained Sentence-BERT base model (used directly in the pretrained-only
# safety-net pipeline, and as the starting point for SetFit fine-tuning).
PRETRAINED_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# --- Reproducibility -------------------------------------------------------
RANDOM_SEED = 42

# --- Verdicts --------------------------------------------------------------
VERDICT_ALLOW = "ALLOW"
VERDICT_FLAG = "FLAG"
