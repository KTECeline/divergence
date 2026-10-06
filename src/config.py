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

MODELS_DIR = PROJECT_ROOT / "models"
FINETUNED_EMBEDDING_DIR = MODELS_DIR / "finetuned_embedding"
CALIBRATION_MODEL_PATH = MODELS_DIR / "calibration_model.pkl"

RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

# --- Split files -----------------------------------------------------------
FINETUNE_SPLIT_PATH = SPLITS_DIR / "finetune.jsonl"
CALIBRATION_SPLIT_PATH = SPLITS_DIR / "calibration.jsonl"
HELD_OUT_TEST_SPLIT_PATH = SPLITS_DIR / "held_out_test.jsonl"

# --- Models ----------------------------------------------------------------
# Pretrained Sentence-BERT base model (used directly in the pretrained-only
# safety-net pipeline, and as the starting point for SetFit fine-tuning).
PRETRAINED_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# --- Reproducibility -------------------------------------------------------
RANDOM_SEED = 42

# --- Verdicts --------------------------------------------------------------
VERDICT_ALLOW = "ALLOW"
VERDICT_FLAG = "FLAG"
