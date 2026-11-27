# Divergence: install and demo guide

This guide takes you from nothing to a verdict on an AI agent skill. You do not need the
research repository, the dataset or any knowledge of how Divergence works.

**What Divergence does:** you give it a skill (a folder with a `SKILL.md`). It runs the skill
once in a sealed sandbox, records what the skill actually did, and compares that with what the
skill's description says it does. If they don't match, the install is blocked and the reason is
shown. It measures whether a skill does what it says, not whether it is malicious.

It is a **research prototype** that extends Microsoft's Agent Governance Toolkit (AGT 4.1.0).
It is not part of Microsoft's AGT distribution.

There are two levels. Do Part 1 first; it takes about 10 minutes and needs no sandbox.

| | Part 1: score a trace | Part 2: check a real skill |
|---|---|---|
| What it does | Scores a recorded trace against a description | Runs the skill in a sandbox, then scores it |
| Runs any skill code? | No | Yes, inside a sealed VM |
| Needs | Python 3.11+ | Python 3.11+, Lima, an OpenRouter key, 30 GiB disk |
| Time | About 10 minutes | About 30 minutes the first time, then about 1 minute per skill |
| Cost | Free | Well under one US cent per skill (LLM calls) |

---

## Requirements

### For Part 1 (scoring only)

| Requirement | Detail | How to check |
|---|---|---|
| macOS or Linux | Windows is untested | |
| Python 3.11 or newer | Tested with 3.11 | `python3 --version` |
| About 1.5 GB of free disk | The Python packages (PyTorch is most of it) plus the 88 MB model | |
| Internet access | To download the packages and the model, once | |

### For Part 2 (checking a real skill), in addition

| Requirement | Detail | How to check |
|---|---|---|
| macOS or Linux | Windows is not supported (the sandbox needs Lima) | |
| [Lima](https://lima-vm.io) 2.0 or newer | Runs the sandbox VM. macOS: `brew install lima` | `limactl --version` |
| 30 GiB free disk, 6 GiB free RAM, 4 CPU cores | For the sandbox VM | |
| An [OpenRouter](https://openrouter.ai) API key | One mode of the trial asks an LLM agent to follow the skill. Create a key at openrouter.ai, add a few US dollars of credit, and **set a low credit limit on the key** | |
| A network that allows package downloads | Ubuntu and Docker packages are downloaded while the sandbox is built. Some campus and office firewalls block this; if so, use home Wi-Fi or a phone hotspot for the one-time setup | |

On Linux, Lima also needs QEMU (`sudo apt install qemu-system`; see Lima's install page).

---

## Part 1: install and score a trace (no sandbox)

### Step 1. Install

Create a clean Python environment and install Divergence into it:

```bash
python3.11 -m venv divergence-env      # or python3.12; plain python3 may be too old on macOS
source divergence-env/bin/activate
pip install divergence-agt
```

This takes a few minutes and also installs AGT 4.1.0. (`divergence-agt` is the package on
PyPI; for the newest code from GitHub use `pip install "git+https://github.com/KTECeline/divergence.git"`.) Check it worked:

```bash
divergence --help
```

You should see the commands `evaluate`, `install` and `setup-sandbox`.

### Step 2. Get the example files

```bash
curl -L https://github.com/KTECeline/divergence/archive/refs/heads/main.tar.gz \
  | tar -xz --strip-components=1 divergence-main/examples
```

This creates an `examples/` folder with two traces and two skills:

```
examples/
  traces/honest.json                   a run that only formats a table
  traces/sneaky.json                   the same run, plus reading a credentials file and contacting a server
  skills/table-formatter-honest/       a skill that does what it says        (for Part 2)
  skills/table-formatter-sneaky/       a skill that also sends a secret away (for Part 2)
```

A trace is the list of actions a skill performed: files read and written, commands run,
servers contacted.

### Step 3. Score the honest trace

```bash
divergence evaluate \
  --description "Formats Markdown tables in a file: aligns the columns and pads the cells." \
  --trace examples/traces/honest.json
```

The first run downloads the model (88 MB) from Hugging Face. You should see:

```
ALLOW: estimated 27% probability that the observed behaviour diverges from the description (FLAG at 50% or more).
Semantic consistency between description and behaviour: 0.82 (0 = unrelated, 1 = same meaning).
No structural red flag fired.
Observed: Reads 2 files in notes, then runs Python script format_table.py, then writes a file in notes
```

### Step 4. Score the sneaky trace

Same description, different behaviour:

```bash
divergence evaluate \
  --description "Formats Markdown tables in a file: aligns the columns and pads the cells." \
  --trace examples/traces/sneaky.json
```

You should see:

```
FLAG: estimated 78% probability that the observed behaviour diverges from the description (FLAG at 50% or more).
Semantic consistency between description and behaviour: 0.64 (0 = unrelated, 1 = same meaning).
Contacted host(s) the description never names: collect.evil-c2.example (weight +2.04).
Read credential file(s) although the description does not mention credentials: /root/.aws/credentials (weight -0.27).
Performed action type(s) the description has no words for: network (weight +0.25).
Observed: Reads a file in notes, then runs Python script format_table.py, then reads credential file ~/.aws/credentials, then contacts domain collect.evil-c2.example, then writes a file in notes
```

The verdict line gives the result, the red-flag lines give the reasons, and the `Observed` line
is the behaviour in plain words.

**Useful options:**
- `--skill-md path/to/SKILL.md` instead of `--description`: reads the description from a skill.
- `--json`: prints the full result object instead of text.
- `--fail-on-flag`: exits with code 1 on FLAG, for use in scripts and CI.

`--trace` also accepts an exported AGT audit log (`{"entries": [...]}`), so if you already
run AGT you can score your own agents' logs this way.

Part 1 is complete. To check a skill that has never been run, continue to Part 2.

---

## Part 2: check a real skill in the sandbox

A new skill has no trace yet, so Divergence must run it once. Because the skill may be
malicious, it runs inside a sealed sandbox:

- **A Linux VM with no shared folders**, so the skill cannot read your files.
- **Fake secrets** (marked `DVGCANARY`) placed where real ones would be, so stealing them shows up in the trace.
- **A fake internet with no route to the real one**, so nothing leaves the VM, but every connection attempt is recorded.
- **An LLM proxy that holds your API key**, so the skill never sees the key.

### Step 5. Install Lima

macOS:

```bash
brew install lima
limactl --version            # needs 2.0 or newer
```

Linux: follow https://lima-vm.io/docs/installation/.

### Step 6. Build the sandbox (one time)

With the Python environment from Step 1 still active:

```bash
divergence setup-sandbox
```

It asks for your OpenRouter API key. The input is hidden; paste the key and press Enter. To
skip the prompt, run `export OPENROUTER_API_KEY=...` first.

This creates a VM named `dvg-lab` and builds everything inside it. It takes 10 to 20 minutes
and downloads Ubuntu, Docker and the sandbox images. It ends with a list of checks:

```
   PASS  image malskillbench/verification-sandbox:latest
   PASS  image dvg/sandbox-synthetic:latest
   PASS  container inetsim is running
   PASS  container fakedns is running
   PASS  container llm-proxy is running
   PASS  patched runner imports in the Python environment
   PASS  no route from dvg-isolated to the real internet
   PASS  any domain resolves to the fake internet (INetSim answered evil-c2.example)
   PASS  LLM proxy refuses non-API paths (403)
   PASS  OpenRouter accepts the key held by the proxy

Sandbox ready.
```

**Every line must say PASS.** If one says FAIL, it says what to do. Running
`divergence setup-sandbox` again resumes where it stopped and skips finished steps.

### Step 7. Check the honest skill

```bash
divergence install --skill-dir examples/skills/table-formatter-honest
```

This takes about a minute. It copies the skill into the VM, runs it, copies the trace back and
scores it. Expected result:

```
Skill table-formatter-honest: ALLOW (suggested AGT decision: allow)

--- direct run ---
ALLOW: estimated 27% probability that the observed behaviour diverges from the description (FLAG at 50% or more).
Semantic consistency between description and behaviour: 0.82 (0 = unrelated, 1 = same meaning).
No structural red flag fired.
Observed: Runs Python script format_table.py, then reads its own skill files

--- instructed run ---
ALLOW: estimated 27% probability ...
...
>>> INSTALLED by AGT -> divergence_installs/.../plugins/table-formatter-honest
AGT audit log: 3 entries, Merkle chain valid: True
```

The skill was run twice. The **direct** run executes the commands in its `SKILL.md` with no AI
involved; the **instructed** run has an LLM agent follow the `SKILL.md`. Both matched the
description, so AGT installed the skill (exit code 0).

### Step 8. Check the sneaky skill

```bash
divergence install --skill-dir examples/skills/table-formatter-sneaky
```

Its script formats the table as promised, then uploads `~/.aws/credentials` to a server its
description never names.
Expected result:

```
Skill table-formatter-sneaky: FLAG (suggested AGT decision: escalate)

--- direct run ---
FLAG: estimated 77% probability that the observed behaviour diverges from the description (FLAG at 50% or more).
Semantic consistency between description and behaviour: 0.68 (0 = unrelated, 1 = same meaning).
Contacted host(s) the description never names: collect.evil-c2.example (weight +2.04).
Read credential file(s) although the description does not mention credentials: /root/.aws/credentials (weight -0.27).
Performed action type(s) the description has no words for: network (weight +0.25).
Observed: Runs Python script format_table.py, then reads its own skill files, then sends data to collect.evil-c2.example (upload) (connection failed), then reads credential file ~/.aws/credentials

--- instructed run ---
ALLOW: estimated 27% probability ...
...
>>> BLOCKED: escalated to a human reviewer (AGT decision: escalate)
```

The direct run caught it, so the skill is blocked (exit code 1). A skill is flagged if **any**
run flags it. Here the instructed run did not see the upload, which is why both runs are done.
The numbers can differ slightly between runs, because the LLM agent does not act identically
every time.

Nothing was really stolen: the credentials were fake, and the upload went to the fake internet.

### Step 9. Check your own skill

Point it at any folder that contains a `SKILL.md`:

```bash
divergence install --skill-dir path/to/your-skill
```

Each run saves `install_report.json` (the verdict and reasons) and `agt_audit_log.json` (AGT's
tamper-evident log of the trial) in `divergence_installs/` in your current folder, and the raw trial
output in `divergence_trials/`.

**Options:**
- `--approve`: if the skill is flagged, show the human-approval path that installs it anyway.
- `--with-agent`: add a third trial run with a safety-aligned agent model.
- `--vm NAME`: use a sandbox VM with another name (create it with `divergence setup-sandbox --vm NAME`).

---

## Reading the result

| Exit code | Meaning |
|---|---|
| 0 | ALLOW: behaviour matches the description, skill installed |
| 1 | FLAG: behaviour diverges from the description, install blocked |
| 2 | Invalid input (a file or argument could not be read). No verdict |
| 3 | The sandbox trial or the sandbox setup failed (for example a timeout, or the LLM refused the key). No verdict |
| 4 | The model could not be found or downloaded |
| 5 | Unexpected error. No verdict (set `DIVERGENCE_DEBUG=1` for details) |
| 6 | Blocked by AGT's own install checks (for example a missing signature) |

**What a verdict does not mean:**
- **ALLOW is not "safe".** Only behaviour that happens during the one-minute trial is seen.
  A payload that waits for a date, a trigger, or runs only at install time is missed.
- **FLAG is not "malicious".** It means the skill did something its description does not
  mention. A well-meaning skill with a vague description can be flagged.
- If the trial observed no actions at all, Divergence says so before the verdict. That means
  nothing was seen, not that the skill is safe.

---

## Managing the sandbox

| Task | Command |
|---|---|
| Re-run the safety checks | `divergence setup-sandbox --check` |
| Replace the OpenRouter key | `divergence setup-sandbox --rekey` |
| Stop the VM (frees RAM) | `limactl stop dvg-lab` |
| Start it again | `limactl start dvg-lab` |
| Delete it completely | `limactl delete dvg-lab` |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `divergence: command not found` | Activate the environment again: `source divergence-env/bin/activate` |
| `pip` says Python is too old | Install Python 3.11+ and recreate the environment with `python3.11 -m venv divergence-env` |
| `model not found` (exit 4) | The machine could not reach huggingface.co. Check your connection and retry |
| `limactl not found` | Install Lima (Step 5) |
| `the agent's LLM call failed: HTTP 401` or `403` (exit 3) | The OpenRouter key is missing, wrong or limited. Replace it: `divergence setup-sandbox --rekey` |
| `the agent's LLM call failed: HTTP 402` (exit 3) | The OpenRouter account or key is out of credit. Add credit and run the install again |
| `the sandbox run did not finish` (exit 3) | The skill ran past the time limit or the sandbox crashed. Run it again; the message names the raw output |
| `VM dvg-lab does not exist` | Run `divergence setup-sandbox` (Step 6) |
| `VM dvg-lab is Stopped` | `limactl start dvg-lab` |
| Setup says the network refuses package downloads | Your network's firewall blocks them. Connect to home Wi-Fi or a phone hotspot and run `divergence setup-sandbox` again |
| FAIL: `OpenRouter answered '401'` | The key is wrong. Run `divergence setup-sandbox --rekey` |
| FAIL: `OpenRouter answered '402'` | The key has no credit left. Add credit at openrouter.ai |

---

## Safety notes

- **Only check untrusted skills through `divergence install`**, which runs them inside the VM.
  Never run an untrusted skill directly on your machine or on Docker Desktop.
- The VM has no shared folders. Files move in and out only through Lima's copy command.
- Your API key is stored only inside the proxy container in the VM. A skill cannot read it, but
  it can spend credit through the proxy, so keep the key's credit limit low.
- The sandbox is built from the MalSkillBench runner (Guo et al., 2026), fetched from its own
  repository. Its licence (academic research use) applies to your use.
