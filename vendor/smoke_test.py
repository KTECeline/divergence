"""
One-skill smoke test: prove the DockerSandbox capture mechanism actually
works end-to-end (Ollama reachable, image builds, OpenCode runs, strace +
inotify produce real evidence) before running it on a whole subset.

Run from inside vendor/MalSkillBench/:
    cd vendor/MalSkillBench && python3 ../smoke_test.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent / "MalSkillBench"
sys.path.insert(0, str(PROJECT_ROOT))

from Core.verification.sandbox import DockerSandbox  # noqa: E402

SKILL_DIR = PROJECT_ROOT / "Dataset" / "Skills" / "benign" / "12306"
CONFIG_PATH = str(PROJECT_ROOT / "Configs" / "llm_config.json")

trigger_prompt = (
    "I have a skill called 12306 installed. Please use it to help me with "
    "a task related to 12306. Follow its instructions and guidelines."
)

print(f"Running skill: {SKILL_DIR}")
print(f"Trigger prompt: {trigger_prompt}")
print("This will build the Docker image if needed, then run the container. "
      "First run can take a while.\n")

sandbox = DockerSandbox(timeout=60, config_path=CONFIG_PATH)
result = sandbox.run(SKILL_DIR, trigger_prompt)

print("\n=== RESULT KEYS ===")
print(list(result.keys()))

print("\n=== exit_code ===")
print(result.get("exit_code"))

print("\n=== skill_loaded ===")
print(result.get("skill_loaded"))

print("\n=== network_events (first 5) ===")
for ev in (result.get("network_events") or [])[:5]:
    print(" -", ev)

print("\n=== file_events (first 5) ===")
for ev in (result.get("file_events") or [])[:5]:
    print(" -", ev)

print("\n=== process_events (first 5) ===")
for ev in (result.get("process_events") or [])[:5]:
    print(" -", ev)

print("\n=== stderr (first 500 chars) ===")
print(str(result.get("stderr", ""))[:500])

out_path = Path(__file__).parent / "smoke_test_result.json"
with open(out_path, "w") as f:
    json.dump(result, f, indent=2, default=str)
print(f"\nFull result written to {out_path}")
