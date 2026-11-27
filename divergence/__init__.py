"""Divergence pipeline package."""

import logging
import os
from pathlib import Path

__version__ = "0.2.1"

# On macOS, importing PyTorch (via sentence-transformers) prints "NOTE: Redirects are
# currently not supported in MacOs." from torch.distributed's elastic launcher, which
# Divergence never uses. Silence that one logger only; nothing else is affected.
logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(logging.ERROR)

# Models are cached locally; without this, every model load first asks huggingface.co
# for updates, and on a slow connection each load stalls on timeouts and retries
# (notebook 05 once took 8 h instead of minutes). Set HF_HUB_OFFLINE=0 to download
# a new model, e.g. for Experiment 4.
# Only in a development checkout (trained model present in models/): a pip-installed
# copy must be able to download the model from the Hub on first use.
if (Path(__file__).resolve().parent.parent / "models" / "finetuned_embedding").is_dir():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
