"""Option B from the research repo: same as `divergence install ...` (see divergence/cli.py).

    .venv/bin/python sandbox/install_skill.py --skill malware/<folder>
    .venv/bin/python sandbox/install_skill.py --skill-dir /path/to/any/skill-folder
    # options: --with-agent, --approve, --vm dvg-lab, --traces-root DIR (Option A: no VM)

Needs the dvg-lab VM running (`limactl start dvg-lab`) with ~/dvg set up as in
sandbox/setup_notes.md. The instructed run calls OpenRouter from inside the VM.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from divergence.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["install", *sys.argv[1:]]))
