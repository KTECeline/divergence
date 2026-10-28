"""Divergence pipeline package."""

import os

# Models are cached locally; without this, every model load first asks huggingface.co
# for updates, and on a slow connection each load stalls on timeouts and retries
# (notebook 05 once took 8 h instead of minutes). Set HF_HUB_OFFLINE=0 to download
# a new model, e.g. for Experiment 4.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
