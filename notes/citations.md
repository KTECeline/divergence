# Citation notes (drafted, not yet placed in the report)

## ClawHub Security Signals — motivating evidence (not used as data)

**Where it goes:** Chapter 1 (Problem Statement) or Chapter 2 (Literature Review), as
real-world corroborating evidence alongside the 38-respondent survey findings.

**Why it's cited but not used as a dataset:** its `skill_bundle_content` field is the
skill's raw source code, not a runtime action trace — verified by pulling ~500 rows via
the HF datasets-server API on 2026-07-28. Labels also come from other static
scanners' verdicts (ClawScan/VirusTotal/SkillInspector), not sandbox-verified ground
truth like MalSkillBench. Using it as training/eval data would mean building a second,
largely parallel static-code-analysis pipeline and would reopen the "install-time attacks
out of scope" boundary already agreed with the supervisor (see CLAUDE.md). Decision:
cite only.

**Draft paragraph:**

> Recent evidence from live agent-skill marketplaces corroborates this problem beyond
> the constructed MalSkillBench benchmark. The ClawHub Security Signals dataset
> (OpenClaw, 2026) — security-scanner assessments of skills distributed through the
> OpenClaw/ClawHub marketplace — includes cases such as a browser-automation skill
> whose bundled source code implements CAPTCHA-solving, Cloudflare-bypass, and
> session-hijacking logic while its declared description gives no indication of this
> behaviour, and a stock-trading skill whose description understates its use of broker
> credentials for persistent, autonomous trade execution. These cases illustrate the
> same description-versus-capability mismatch this project targets, occurring in a live,
> non-synthetic marketplace rather than a constructed benchmark. Note that ClawHub's
> assessments are derived from static analysis of source code rather than observed
> runtime behaviour, so the dataset was not incorporated into Divergence's training or
> evaluation pipeline — it is cited here solely as independent evidence that the
> underlying problem is real in production settings.

**Citation (APA-style, verify format against your department's required style):**
OpenClaw. (2026). *ClawHub Security Signals* [Data set]. Hugging Face.
https://huggingface.co/datasets/OpenClaw/clawhub-security-signals

**In-text:** (OpenClaw, 2026)

---

## Phase 1 trace capture — OpenCode-as-agent-proxy (methodology/scope note)

**Where it goes:** Chapter 3, Deployment or Modelling phase writeup (3.2.3.4/3.2.3.6),
as a stated scope/limitation note — not hidden, explicitly acknowledged.

**The decision:** MalSkillBench's public release ships only `SKILL.md` (description) +
`scripts/` (code) per sample — no runtime trace (`_evidence.json` is generated during
the authors' own verification but explicitly excluded from the release). To get real
behavioural traces for Phase 1, we run each sampled skill ourselves through
MalSkillBench's own open-sourced verification sandbox
(`Core/verification/sandbox.py`, repo: github.com/lxyeternal/MalSkillBench), which
executes the skill inside a Docker container via **OpenCode** (a generic, portable
AI coding-agent CLI) while `strace`/`inotifywait` capture real OS-level behaviour
(file access, network calls, commands run). We use the raw captured behaviour
directly; we do not reconstruct the authors' `_expected.json`/pass-fail verification
layer, since Divergence's own structural-flag rules and calibration model perform
that judgment independently.

**Why OpenCode is an acceptable stand-in, not a shortcut:** inspecting the released
`SKILL.md` files confirms they are written in a portable, cross-agent format —
e.g. `compatible-with: claude-code, codex, openclaw` frontmatter, and OpenClaw-specific
`clawdbot` metadata blocks on others. The same natural-language instructions and tool
calls (read a file, fetch a URL, run a script) are meant to execute identically
regardless of which compatible agent interprets them. OpenCode is one such agent;
capturing OS-level behaviour under it is a reasonable proxy for "an AI agent executing
this skill's instructions" in general.

**Stated limitation (be explicit about this, don't bury it):** OpenCode is not the
literal OpenClaw/AGT runtime this project ultimately targets. This is precisely why
Phase 2 exists as a separate validation step — it re-checks whether a system built on
Phase 1's OpenCode-captured traces still holds up against traces captured from the
real OpenClaw + AGT stack, rather than assuming the proxy is a perfect match.

**Draft paragraph:**

> Runtime traces for the Phase 1 pipeline were captured using MalSkillBench's own
> open-sourced verification sandbox, in which each sampled skill is executed inside an
> instrumented Docker container by OpenCode — a generic, portable AI coding-agent CLI —
> while `strace` and `inotifywait` record real operating-system-level behaviour. This is
> an appropriate proxy rather than a shortcut: the sampled `SKILL.md` files are
> themselves written in a portable format explicitly compatible across multiple agent
> runtimes, including OpenClaw, so the observed behaviour reflects what the skill's
> instructions cause to happen at the system level, independent of which compatible
> agent issues them. We do not claim this is equivalent to execution under the real
> OpenClaw/AGT runtime, however; validating that the resulting model generalises to
> traces captured from the actual target platform is deferred to Phase 2, by design.
