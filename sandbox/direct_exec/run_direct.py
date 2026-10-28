"""Stage 3 direct-execution runner.

Runs each listed skill's OWN scripts directly under the sealed DockerSandbox
(no agent, no LLM, so no refusals and $0 spend), to collect traces of what the
skill's code actually does. This is the second execution mode in the report:
agent-mediated (batch_out/) vs direct (direct_out/). The two are kept separate
and never merged silently. Benign skills MUST be run through here too, or the
model would learn "direct-mode trace == malicious".

Containment is the sandbox's, unchanged: dvg-isolated network (no egress),
cap-drop ALL, INetSim absorbs and logs every outbound attempt. The only change
from an agent run is the entrypoint, swapped via DVG_DIRECT_ENTRYPOINT.

Each run writes results/<label>/<folder>.json (identical shape to batch_out, so
the Stage 3 loader/normaliser read it unchanged) and a summary.csv row.

Run inside the VM:
    source ~/dvg/.venv/bin/activate && cd ~/dvg/MalSkillBench
    DVG_SANDBOX_IMAGE=dvg/sandbox-synthetic \
    DVG_DIRECT_ENTRYPOINT=~/dvg/direct_exec/entrypoint_direct.sh \
    python3 ~/dvg/direct_exec/run_direct.py \
        --ids ~/dvg/synthetic_user/pilot_ids.txt --out ~/dvg/direct_out
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent / "vendor" / "MalSkillBench"
# In the VM the layout is flatter (~/dvg/MalSkillBench); allow an override.
PROJECT_ROOT = Path(os.environ.get("DVG_MSB_ROOT", PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from Core.verification.sandbox import DockerSandbox  # noqa: E402

SKILLS_DIR = PROJECT_ROOT / "Dataset" / "Skills"
CONFIG_PATH = str(PROJECT_ROOT / "Configs" / "llm_config.json")
FIELDS = ["label", "skill", "mode", "model", "trigger", "duration_s",
          "timed_out", "n_scripts", "exit_code", "error"]


def read_ids(path: Path) -> list[tuple[str, str]]:
    ids = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            lab, folder = ln.split("/", 1)
            ids.append((lab, folder))
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", type=Path, required=True, help="file of <label>/<skill> ids")
    ap.add_argument("--out", type=Path, default=HERE.parent.parent / "direct_out")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--skills-dir", type=Path, default=SKILLS_DIR)
    args = ap.parse_args()

    if not os.environ.get("DVG_DIRECT_ENTRYPOINT"):
        sys.exit("Set DVG_DIRECT_ENTRYPOINT to entrypoint_direct.sh before running.")

    ids = read_ids(args.ids)
    args.out.mkdir(parents=True, exist_ok=True)
    summary_path = args.out / "summary.csv"
    done = set()
    if summary_path.exists():
        with open(summary_path, newline="", encoding="utf-8") as f:
            done = {(r["label"], r["skill"]) for r in csv.DictReader(f)}

    sandbox = DockerSandbox(timeout=args.timeout, config_path=CONFIG_PATH)
    new_rows = []
    for n, (lab, folder) in enumerate(ids, 1):
        if (lab, folder) in done:
            print(f"[{n}/{len(ids)}] skip (done) {lab}/{folder}")
            continue
        skill_dir = args.skills_dir / lab / folder
        if not skill_dir.is_dir():
            print(f"[{n}/{len(ids)}] MISSING {skill_dir}")
            continue
        print(f"[{n}/{len(ids)}] direct {lab}/{folder} ...", flush=True)
        start = time.monotonic()
        # trigger is unused in direct mode, but DockerSandbox.run requires one.
        result = sandbox.run(skill_dir, "DIRECT_EXECUTION_NO_AGENT")
        duration = round(time.monotonic() - start, 2)

        res_path = args.out / "results" / lab / f"{folder}.json"
        res_path.parent.mkdir(parents=True, exist_ok=True)
        res_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

        err = result.get("error", "") if isinstance(result, dict) else ""
        procs = result.get("process_events", []) if isinstance(result, dict) else []
        n_scripts = sum(1 for e in procs if isinstance(e, dict)
                        and e.get("syscall") == "execve"
                        and any(x in str(e.get("command", "")) for x in ("python3", "bash")))
        row = {
            "label": lab, "skill": folder, "mode": "direct", "model": "none",
            "trigger": "direct", "duration_s": duration,
            "timed_out": "timed out" in str(err).lower(),
            "n_scripts": n_scripts, "exit_code": result.get("exit_code", ""),
            "error": err[:200],
        }
        new_rows.append(row)
        write_header = not summary_path.exists()
        with open(summary_path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if write_header:
                w.writeheader()
            w.writerow(row)

    print(f"\nDone. {len(new_rows)} new direct runs -> {args.out}")


if __name__ == "__main__":
    main()
