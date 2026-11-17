"""Where the sandbox build files live, in a clone and in a pip-installed copy.

`divergence setup-sandbox` builds the sealed Lima VM that `divergence install` runs a
skill in. The files it needs (the VM template, the in-VM provisioning script, the
trial runners, the synthetic-user image) live in the repo under sandbox/ and vendor/.

A pip install carries a copy of exactly these files inside the package, under
divergence/_sandbox/, with the same relative paths (setup.py copies them at build
time). So the scripts work unchanged from either root.

This module imports nothing from the package: setup.py reads BUNDLE from it.
"""

from pathlib import Path

# Paths relative to the repo root. Directories are copied whole.
BUNDLE = [
    "sandbox/setup_sandbox.sh",
    "sandbox/lima",
    "sandbox/provision",
    "sandbox/malskillbench_patches.diff",
    "sandbox/demo_trial.sh",
    "sandbox/direct_exec",
    "sandbox/instructed_agent",
    "sandbox/synthetic_user",
    "vendor/batch_run.py",
    "vendor/pilot_run.py",
]
BUNDLE_DIR = "_sandbox"  # inside the divergence package

_PKG = Path(__file__).resolve().parent
_REPO = _PKG.parent


def sandbox_root() -> Path:
    """The folder holding sandbox/ and vendor/: the repo in a clone, else the bundled copy."""
    if (_REPO / "pyproject.toml").is_file() and (_REPO / "sandbox" / "setup_sandbox.sh").is_file():
        return _REPO
    return _PKG / BUNDLE_DIR


def setup_script() -> Path:
    return sandbox_root() / "sandbox" / "setup_sandbox.sh"


def trial_script() -> Path:
    return sandbox_root() / "sandbox" / "demo_trial.sh"
