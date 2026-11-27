# Divergence: tester guide

Divergence checks whether an AI agent skill **does what its description says**. It runs the
skill in a sealed sandbox, watches what it does, and blocks the install if the behaviour doesn't
match the description.

It's a research prototype built on Microsoft's Agent Governance Toolkit (AGT 4.1.0).

- **Part 1** (10 min, free): score example traces. No sandbox needed.
- **Part 2** (30 min the first time): check real skills in a sandbox VM.

---

## Part 1: score a trace

**You need:** macOS or Linux, Python 3.11+ (check with `python3 --version`), about 1.5 GB of free disk.

**1. Install**

```bash
python3.11 -m venv divergence-env
source divergence-env/bin/activate
pip install divergence-agt
divergence --help
```

You should see `evaluate`, `install` and `setup-sandbox`.

**2. Get the examples**

```bash
curl -L https://github.com/KTECeline/divergence/archive/refs/heads/main.tar.gz \
  | tar -xz --strip-components=1 divergence-main/examples
```

**3. Score an honest trace**

```bash
divergence evaluate \
  --description "Formats Markdown tables in a file: aligns the columns and pads the cells." \
  --trace examples/traces/honest.json
```

Expected: `ALLOW` (about 18%). The first run downloads an 88 MB model.

**4. Score a sneaky trace** (same description, but it also steals credentials)

```bash
divergence evaluate \
  --description "Formats Markdown tables in a file: aligns the columns and pads the cells." \
  --trace examples/traces/sneaky.json
```

Expected: `FLAG` (about 84%), with reasons such as `Contacted host(s) the description never names: collect.evil-c2.example`.

Part 1 is done.

---

## Part 2: check a real skill in the sandbox

**You also need:**
- [Lima](https://lima-vm.io) 2.0+. On macOS run `brew install lima`. On Linux follow Lima's install page.
- 30 GB of free disk, 6 GB of free RAM, 4 CPU cores
- An [OpenRouter](https://openrouter.ai) API key with a few dollars of credit. **Set a low credit limit on the key.**
- A network that allows downloads. If setup fails on campus Wi-Fi, use home Wi-Fi or a phone hotspot.

**5. Build the sandbox** (one time, 10–20 min)

```bash
divergence setup-sandbox
```

Paste your OpenRouter key when it asks (the key stays hidden as you type). At the end, **every line must say PASS**,
followed by `Sandbox ready.` If something fails, run the same command again; it picks up where it stopped.

**6. Check the honest skill**

```bash
divergence install --skill-dir examples/skills/table-formatter-honest
```

Expected: `ALLOW` and `>>> INSTALLED by AGT`.

**7. Check the sneaky skill**

```bash
divergence install --skill-dir examples/skills/table-formatter-sneaky
```

Expected: `FLAG` and `>>> BLOCKED`. Nothing was actually stolen: the secrets are fake, and the
sandbox's internet is fake too.

**8. Check your own skill** (optional)

Any folder with a `SKILL.md` works:

```bash
divergence install --skill-dir path/to/your-skill
```

**Where to find skills:**

| Where | What's there |
|---|---|
| [Anthropic's skills](https://github.com/anthropics/skills) | Official examples. Start here; these should come back ALLOW |
| [antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | The biggest collection, about 2,700 skills |
| [kodustech/awesome-agent-skills](https://github.com/kodustech/awesome-agent-skills) | Software engineering skills |
| ClawHub | The OpenClaw marketplace. Community skills that nobody has vetted |
| skills.sh | A directory ranked by install count |

To use a skill from GitHub:
1. Click **Code → Download ZIP** and unzip it.
2. Find the folder that contains the skill's `SKILL.md`.
3. Run `divergence install --skill-dir path/to/that-folder`.

⚠️ **Never run a downloaded skill's scripts yourself.** Let `divergence install` run them inside the VM.

---

## What the result means

- **ALLOW** means the skill did only what its description says. It does **not** mean the skill is safe.
- **FLAG** means the skill did something its description doesn't mention. It does **not** mean the skill is malicious.

## When you're done

```bash
limactl stop dvg-lab          # pause the VM
limactl delete -f dvg-lab     # delete it and free 30 GB
```

## If something goes wrong

| Problem | Fix |
|---|---|
| `divergence: command not found` | `source divergence-env/bin/activate` |
| Python too old | Install Python 3.11+ and redo step 1 |
| `model not found` | Check your internet and retry |
| `limactl not found` | Install Lima |
| HTTP `401` / `403` | Wrong key: `divergence setup-sandbox --rekey` |
| HTTP `402` | Out of credit: top up at openrouter.ai |
| `VM dvg-lab is Stopped` | `limactl start dvg-lab` |
| `VM dvg-lab does not exist` | Redo step 5 |
| Anything else | Run it again. If it still fails, send me the full error message |
