"""Check that a new commit of the Hugging Face model repo changed the model card only.

    python release/verify_hf_weights.py <old_commit> <new_commit>

Compares the two commits' file lists as the Hub reports them (a content hash per
file: SHA-256 for the weights, git blob SHA-1 for the small files) and then checks
the weights and the calibration file against the local copies in models/. Read-only:
it downloads nothing but the two file lists and changes nothing. Exits 1 if any file
other than README.md differs, or if a local hash does not match.
"""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = "KTECeline/divergence-minilm-l6"
MODELS = Path(__file__).resolve().parent.parent / "models"
LOCAL = {"model.safetensors": MODELS / "finetuned_embedding" / "model.safetensors",
         "calibration_model.json": MODELS / "calibration_model.json"}


def tree(revision: str) -> dict[str, str]:
    """path -> content hash, for every file in the repo at that commit."""
    with urllib.request.urlopen(f"https://huggingface.co/api/models/{REPO}/tree/{revision}", timeout=60) as r:
        return {f["path"]: (f.get("lfs") or {}).get("oid", f["oid"]) for f in json.load(r)}


def local_hash(path: Path, lfs: bool) -> str:
    data = path.read_bytes()
    if lfs:  # large files: the Hub stores their SHA-256
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # small files: git's blob hash


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    old, new = tree(sys.argv[1]), tree(sys.argv[2])
    changed = sorted(p for p in old.keys() | new.keys() if old.get(p) != new.get(p))
    print(f"files in old commit: {len(old)}, in new commit: {len(new)}")
    print("files that differ:", ", ".join(changed) or "none")
    ok = set(changed) <= {"README.md"}
    for name, path in LOCAL.items():
        if not path.is_file():
            print(f"{name}: no local copy at {path}, not compared")
            continue
        same = new.get(name) == old.get(name) == local_hash(path, lfs=len(new.get(name, "")) == 64)
        print(f"{name}: {new.get(name)}  old commit = new commit = local file: {same}")
        ok = ok and same
    print("RESULT:", "only the model card changed; weights and calibration are unchanged" if ok
          else "STOP: something other than README.md differs, or a local file does not match")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
