"""Normalise one sandbox run into an ordered, AGT-style action list.

Input: the DockerSandbox result JSON written by vendor/batch_run.py.
Output: a list of actions, in the order the agent took them, each one a small
dict that reads like an audit-log entry:

    {"seq": 3, "step": 2, "source": "tool", "tool": "bash",
     "action": "command", "target": "python3 scripts/run.py", "status": "ok"}
    {"seq": 4, "step": 2, "source": "process", "tool": "bash",
     "action": "network_connect", "target": "172.30.0.2:443", "status": "failed"}

Two layers, merged per step:
  * "tool"    — the agent's tool calls (skill, bash, read, write, edit, glob,
                grep, webfetch, task), in order. This is the backbone, because
                the strace event lists lose cross-category order.
  * "process" — what the bash call caused at OS level (exec, file, network),
                attributed to the call through the process tree (clone events)
                rooted at its `bash -c <command>` exec.

Deliberately left out:
  * the agent's text and tool outputs. Divergence sees actions, as AGT's audit
    log does, not the agent's commentary ("this script is malicious"), which
    would leak the label;
  * OpenCode's own activity (its LLM calls, model/npm lookups, library loads);
  * system noise: shared-library and interpreter reads, caches, /proc, /sys.

Normalisation is factual: it does not decide what is sensitive. That is the
job of structural_flags.py and trace_to_text.py (Stage 4).
"""

import re
from pathlib import PurePosixPath

SKILL_DIRS = ("/workspace/.opencode/skills/target-skill", "/workspace/skill")
SANDBOX_DNS = ("127.0.0.11", "172.30.0.4")  # Docker's resolver and the fakedns sinkhole
LLM_PROXY = "172.30.0.3"

# Paths whose reads are library/interpreter/cache noise. Writes are kept everywhere.
NOISE_READ_PREFIXES = (
    "/usr/", "/lib/", "/lib64/", "/bin/", "/sbin/", "/proc/", "/sys/", "/dev/",
    "/etc/ld.so", "/etc/ssl/", "/etc/alternatives/", "/etc/localtime",
    "/etc/nsswitch.conf", "/etc/host.conf", "/etc/gai.conf", "/etc/resolv.conf",
    "/etc/python", "/etc/mime.types", "/etc/os-release", "/etc/apt/",
    # every ls/find/ps looks up user names here; an explicit `cat /etc/passwd`
    # still shows in the command and its process_exec
    "/etc/passwd", "/etc/group", "/etc/nsswitch",
    "/root/.cache/", "/root/.npm/", "/root/.local/share/opencode", "/root/.config/opencode",
    "/root/.local/state/opencode", "/tmp/evidence",
)
NOISE_ANY = ("/__pycache__/", "/node_modules/", "/site-packages/", "/dist-packages/")
NOISE_WRITE_PREFIXES = (
    "/proc/", "/sys/", "/dev/", "/root/.cache/", "/root/.npm/", "/root/.local/share/opencode",
    "/root/.config/opencode", "/root/.local/state/opencode", "/tmp/evidence",
)

# The closing quote may be missing: the upstream parser cuts args at 300 chars.
_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)(?:"(?:\.\.\.)?|$)')
_INET = re.compile(r'sin6?_port=htons\((\d+)\).*?(?:inet_addr|inet_pton\(AF_INET6?)\("?([0-9a-fA-F.:]+)"?\)')


def strace_unescape(s: str) -> str:
    """Decode strace's C-style escapes (\\", \\n, \\350...) back to text."""
    out, i = bytearray(), 0
    simple = {"n": 10, "t": 9, "r": 13, "v": 11, "f": 12, "\\": 92, '"': 34}
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in simple:
                out.append(simple[nxt]); i += 2; continue
            m = re.match(r"[0-7]{1,3}", s[i + 1:])
            if m:
                out.append(int(m.group(0), 8) & 0xFF); i += 1 + len(m.group(0)); continue
            if nxt == "x" and re.match(r"[0-9a-fA-F]{2}", s[i + 2:i + 4]):
                out.append(int(s[i + 2:i + 4], 16)); i += 4; continue
        out.extend(c.encode("utf-8")); i += 1
    return out.decode("utf-8", errors="replace")


def parse_execve_argv(args: str) -> list[str]:
    """argv of an execve line (first quoted string is the path, the rest argv).

    The upstream parser keeps 300 chars of args and strace 256 per string, so
    long argv is cut; a truncated string is returned as-is (prefix)."""
    quoted = [strace_unescape(m.group(1)) for m in _QUOTED.finditer(args)]
    return quoted[1:] if len(quoted) > 1 else quoted


def _is_noise_read(path: str) -> bool:
    p = path.rstrip("/") + "/"  # so the bare directory /root/.cache matches too
    return p.startswith(NOISE_READ_PREFIXES) or any(n in p for n in NOISE_ANY)


def _is_noise_write(path: str) -> bool:
    p = path.rstrip("/") + "/"
    return p.startswith(NOISE_WRITE_PREFIXES) or any(n in p for n in NOISE_ANY)


def _skill_relative(path: str) -> str:
    """Show skill files as skill/<rel> so the two mount points read the same."""
    for d in SKILL_DIRS:
        if path == d or path.startswith(d + "/"):
            return "skill/" + path[len(d):].lstrip("/")
    return path


def _open_mode(args: str) -> str:
    if "O_WRONLY" in args or "O_RDWR" in args or "O_CREAT" in args or "O_TRUNC" in args:
        return "write"
    return "read"


def _tool_calls(result: dict) -> list[dict]:
    calls = []
    for ev in (result.get("agent_json") or {}).get("events", []) or []:
        part = ev.get("part") or {}
        if part.get("type") != "tool":
            continue
        st = part.get("state") or {}
        calls.append({
            "tool": part.get("tool") or "?",
            "input": st.get("input") or {},
            "status": "ok" if st.get("status") == "completed" else (st.get("status") or "?"),
        })
    return calls


def _process_tree(process_events: list[dict]) -> dict[str, str]:
    """child pid -> parent pid, from completed clone/fork/vfork events."""
    parent = {}
    for p in process_events:
        if p.get("syscall") in ("clone", "clone3", "fork", "vfork"):
            ret = p.get("return")
            if isinstance(ret, int) and ret > 0:
                parent.setdefault(str(ret), str(p.get("pid")))
    return parent


def _bash_roots(process_events: list[dict]) -> list[tuple[str, str]]:
    """(pid, command) for every `bash -c <command>` exec, in pid order.

    Pids grow monotonically inside a short-lived container, so pid order is
    the order the shells were started (the event list itself is not ordered:
    unfinished execs are appended at the end by the upstream parser)."""
    roots, seen = [], set()
    for p in process_events:
        if p.get("syscall") != "execve":
            continue
        argv = parse_execve_argv(p.get("args", ""))
        if len(argv) >= 3 and PurePosixPath(argv[0]).name in ("bash", "sh") and argv[1] == "-c":
            pid = str(p.get("pid"))
            if pid not in seen:
                seen.add(pid)
                roots.append((pid, argv[2]))
    roots.sort(key=lambda r: int(r[0]) if r[0].isdigit() else 0)
    return roots


def _match_bash_calls(calls: list[dict], roots: list[tuple[str, str]]) -> dict[int, str]:
    """Tool-call index -> root pid. Match on the command prefix (strace cuts
    long strings), in order; a root that matches no call is a shell started by
    skill code itself and stays attached to whichever call spawned it."""
    mapping, r = {}, 0
    for i, c in enumerate(calls):
        if c["tool"] != "bash":
            continue
        cmd = str(c["input"].get("command", ""))
        for j in range(r, len(roots)):
            pre = roots[j][1][:120]
            if pre and cmd.startswith(pre.rstrip(".")):
                mapping[i] = roots[j][0]
                r = j + 1
                break
    return mapping


def _owner(pid: str, parent: dict[str, str], root_of: dict[str, int], cache: dict) -> int | None:
    """Tool-call index whose bash subtree contains pid, or None (OpenCode itself)."""
    if pid in cache:
        return cache[pid]
    chain, cur, found = [], pid, None
    for _ in range(64):
        if cur in root_of:
            found = root_of[cur]
            break
        chain.append(cur)
        if cur not in parent:
            break
        cur = parent[cur]
    for c in chain + [pid]:
        cache[c] = found
    return found


def normalise(result: dict) -> list[dict]:
    """Ordered, de-duplicated action list for one run (see module docstring)."""
    calls = _tool_calls(result)
    pevents = result.get("process_events") or []
    parent = _process_tree(pevents)
    call_root = _match_bash_calls(calls, _bash_roots(pevents))
    root_of = {pid: i for i, pid in call_root.items()}
    cache: dict = {}

    # OS-level effects grouped by the tool call that caused them
    effects: dict[int, list[tuple[str, str, str]]] = {}

    def add(pid, action, target, status):
        i = _owner(str(pid), parent, root_of, cache)
        if i is not None:
            effects.setdefault(i, []).append((action, target, status))

    for p in pevents:
        if p.get("syscall") != "execve":
            continue
        pid = str(p.get("pid"))
        if pid in root_of:
            continue  # the bash -c itself is the tool call
        argv = parse_execve_argv(p.get("args", ""))
        if not argv:
            continue
        target = " ".join(_skill_relative(a) for a in argv)[:200]
        # -1 here is usually an <unfinished> exec, not a failure; keep as ok
        add(pid, "process_exec", target, "ok")

    for f in result.get("file_events") or []:
        sc, path = f.get("syscall"), f.get("path") or ""
        if sc == "inotify" or not path.startswith("/"):
            continue  # inotify has no pid; its writes are also seen by strace
        ok = isinstance(f.get("return"), int) and f["return"] >= 0
        if sc in ("unlinkat", "unlink", "rmdir"):
            if not _is_noise_write(path):
                add(f.get("pid"), "file_delete", _skill_relative(path), "ok" if ok else "failed")
            continue
        if sc in ("mkdirat", "mkdir"):
            continue
        mode = _open_mode(f.get("args", ""))
        if mode == "write" and not _is_noise_write(path):
            add(f.get("pid"), "file_write", _skill_relative(path), "ok" if ok else "failed")
        elif mode == "read" and not _is_noise_read(path):
            add(f.get("pid"), "file_read", _skill_relative(path), "ok" if ok else "failed")

    for n in result.get("network_events") or []:
        pid = n.get("pid")
        for d in n.get("dns_domains") or []:
            add(pid, "dns_lookup", d, "ok")
        if n.get("syscall") not in ("connect", "sendto", "sendmsg"):
            continue
        m = _INET.search(n.get("args", ""))
        if not m:
            continue  # AF_UNIX / netlink
        port, ip = m.group(1), m.group(2)
        if ip in SANDBOX_DNS or ip.startswith("127.") or ip == "0.0.0.0" or ip == LLM_PROXY:
            continue
        ret = n.get("return")
        ok = isinstance(ret, int) and ret >= 0
        add(pid, "network_connect", f"{ip}:{port}", "ok" if ok else "failed")

    actions: list[dict] = []

    def emit(step, source, tool, action, target, status):
        actions.append({"seq": len(actions), "step": step, "source": source, "tool": tool,
                        "action": action, "target": target, "status": status})

    for i, c in enumerate(calls):
        tool, inp, st = c["tool"], c["input"], c["status"]
        if tool == "skill":
            emit(i, "tool", tool, "skill_load", str(inp.get("name", "")), st)
        elif tool == "bash":
            emit(i, "tool", tool, "command", str(inp.get("command", ""))[:300], st)
        elif tool == "read":
            emit(i, "tool", tool, "file_read", _skill_relative(str(inp.get("filePath", ""))), st)
        elif tool in ("write", "edit"):
            emit(i, "tool", tool, "file_write", _skill_relative(str(inp.get("filePath", ""))), st)
        elif tool in ("glob", "grep"):
            target = f"{inp.get('pattern', '')} in {_skill_relative(str(inp.get('path') or '.'))}"
            emit(i, "tool", tool, "file_search", target, st)
        elif tool == "webfetch":
            emit(i, "tool", tool, "web_fetch", str(inp.get("url", "")), st)
        elif tool == "task":
            emit(i, "tool", tool, "subagent", str(inp.get("description", ""))[:120], st)
        else:
            continue  # todowrite etc.: planning, no effect on the system
        seen = set()
        for action, target, status in effects.get(i, []):
            key = (action, target)
            if key in seen:
                continue
            seen.add(key)
            emit(i, "process", tool, action, target, status)
    return actions


def attribution_coverage(result: dict) -> float:
    """Share of bash tool calls matched to a `bash -c` process (data-quality check)."""
    calls = _tool_calls(result)
    n = sum(1 for c in calls if c["tool"] == "bash")
    if n == 0:
        return 1.0
    return len(_match_bash_calls(calls, _bash_roots(result.get("process_events") or []))) / n
