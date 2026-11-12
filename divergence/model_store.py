"""Where the trained Divergence model comes from.

The model is two files' worth of state: the fine-tuned sentence encoder (~88 MB)
and the logistic-regression calibrator (a 4 KB JSON). They are not in git, so a
pip-installed copy finds them in this order:

  1. DIVERGENCE_MODEL_DIR  a folder you point at (encoder files + calibration_model.json)
  2. the repo's models/    a development checkout (models/finetuned_embedding/ +
                           models/calibration_model.json), exactly as trained
  3. Hugging Face Hub      HF_MODEL_REPO, downloaded once and cached by huggingface_hub

The Hub repo holds the encoder files at its root plus calibration_model.json,
i.e. the same layout as option 1. Pin HF_MODEL_REVISION to a commit hash so a
later upload can't silently change the model a report's numbers came from.
"""

import os
from pathlib import Path

from divergence.config import CALIBRATION_MODEL_PATH, FINETUNED_EMBEDDING_DIR

HF_MODEL_REPO = os.environ.get("DIVERGENCE_HF_REPO", "KTECeline/divergence-minilm-l6")
# Pinned to the uploaded v0.1.0 commit (2026-11-07): the model behind the reported results.
# After retraining + re-uploading, move this pin to the new commit on purpose.
HF_MODEL_REVISION = os.environ.get("DIVERGENCE_HF_REVISION", "e50efa630ea4ee6f8e5958217595e3dd700136d7")
CALIBRATION_FILE = "calibration_model.json"


class ModelNotFound(RuntimeError):
    pass


def _bundle(folder: Path) -> tuple[Path, Path] | None:
    folder = Path(folder)
    if (folder / "config.json").is_file() and (folder / CALIBRATION_FILE).is_file():
        return folder, folder / CALIBRATION_FILE
    return None


def resolve_model() -> tuple[Path, Path]:
    """(encoder folder, calibration JSON) for the trained Divergence model."""
    if os.environ.get("DIVERGENCE_MODEL_DIR"):
        found = _bundle(Path(os.environ["DIVERGENCE_MODEL_DIR"]).expanduser())
        if not found:
            raise ModelNotFound(f"DIVERGENCE_MODEL_DIR={os.environ['DIVERGENCE_MODEL_DIR']} needs the encoder "
                                f"files (config.json, model.safetensors, ...) and {CALIBRATION_FILE}")
        return found
    if (FINETUNED_EMBEDDING_DIR / "config.json").is_file() and CALIBRATION_MODEL_PATH.is_file():
        return FINETUNED_EMBEDDING_DIR, CALIBRATION_MODEL_PATH
    try:
        from huggingface_hub import snapshot_download
        folder = Path(snapshot_download(HF_MODEL_REPO, revision=HF_MODEL_REVISION))
    except Exception as e:  # offline, repo missing, no huggingface_hub, ...
        raise ModelNotFound(f"could not get the Divergence model from Hugging Face ({HF_MODEL_REPO}@"
                            f"{HF_MODEL_REVISION}): {e}. Set DIVERGENCE_MODEL_DIR to a local copy instead.") from e
    found = _bundle(folder)
    if not found:
        raise ModelNotFound(f"{HF_MODEL_REPO} is missing the encoder files or {CALIBRATION_FILE}")
    return found
