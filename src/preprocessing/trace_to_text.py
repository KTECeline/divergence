"""Enriched trace-to-text conversion (pipeline Step 2, Option 1).

Build order item 5 — the biggest engineering task and an original
contribution. Converts a raw action trace into enriched natural-language
text via rule-based templates. NOT a flat template: sensitive action types
(e.g. sending data to an external, previously unseen domain; credential
access) must be named explicitly in the output text.

Develop and test iteratively in notebooks/03_trace_to_text_enriched.ipynb,
with unit tests in tests/test_trace_to_text.py written as you go.

Design rules (each one is a reportable decision):
  * The text is a function of the TRACE ONLY. Whether a domain is mentioned in
    the description is a comparison, so it belongs to structural_flags.py.
  * Tool-internal reads are dropped: curl reading ~/.curlrc and ~/.netrc, npm
    reading ~/.npmrc, libc reading /etc/hosts. The skill did not ask for them.
  * Every process is described by what it does ("downloads from bun.sh"), not
    by its raw command line, so the text shares vocabulary with descriptions.
  * Connections to the sandbox sinkhole are folded into the command that made
    them, since the sinkhole IP says nothing about the real destination.
  * Sensitive actions get HIGH priority. When the text would exceed the
    encoder's token limit, LOW then MEDIUM phrases are dropped first, so the
    payload is never the part that gets cut off.
"""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

from src.data.outcome import PERSISTENCE_RE, SCRIPT_EXT, SENSITIVE_RE

SINKHOLE_IP = "172.30.0.2"  # INetSim: the fake DNS resolves every domain here
SKILL_PREFIXES = ("/workspace/.opencode/skills/target-skill", "/workspace/skill", "skill/", "skill")
TOOL_CONFIG_READS = re.compile(
    r"(/\.curlrc$|/curlrc$|/\.npmrc$|/etc/npmrc$|/pip\.conf$|/\.wgetrc$|/etc/hosts$|/etc/netsvc\.conf$|"
    r"/etc/svc\.conf$|/etc/debian_version$|/etc/dpkg/|/\.dpkg\.cfg$|/etc/gcrypt/|/var/lib/(apt|dpkg)/)")
NETRC_READERS = {"curl", "wget", "git", "pip", "pip3", "python", "python3"}  # read ~/.netrc by themselves (python: requests)

LOW, MID, HIGH = 0, 1, 2
WRAPPERS = {"timeout", "nohup", "nice", "stdbuf", "time", "exec", "command"}
PLUMBING = {
    "cat", "head", "tail", "less", "more", "grep", "egrep", "sed", "awk", "sort", "uniq", "wc", "echo",
    "printf", "which", "true", "false", "test", "[", "sleep", "date", "tr", "cut", "xargs", "basename",
    "dirname", "pwd", "diff", "jq", "tee", "touch", "mkdir", "cp", "mv", "ln", "rm", "realpath",
    "readlink", "seq", "clear", "dpkg", "cd", "type", "file", "stat", "md5sum", "sha256sum", "mktemp",
}
LISTING = {"ls", "find", "tree", "du", "df"}
SYSINFO = {"whoami", "id", "uname", "hostname", "lsb_release", "getent", "ps", "ifconfig", "ip", "nproc"}
ARCHIVE = {"tar", "zip", "unzip", "gzip", "gunzip", "7z", "bzip2", "xz"}
INSTALLERS = {"pip", "pip3", "npm", "pnpm", "yarn", "apt", "apt-get", "uv", "poetry", "brew", "gem", "cargo"}
INTERPRETERS = {"python": "Python", "python3": "Python", "node": "Node.js", "bash": "shell", "sh": "shell",
                "zsh": "shell", "ruby": "Ruby", "perl": "Perl", "php": "PHP", "tsx": "TypeScript",
                "ts-node": "TypeScript", "deno": "Deno", "bun": "Bun"}
CLOUD_CLIS = {"docker", "kubectl", "gh", "aws", "gcloud", "az", "terraform", "heroku", "vercel"}
MINERS = re.compile(r"\b(xmrig|minerd|cpuminer|ethminer|nbminer)\b", re.I)
DEV_TCP = re.compile(r"/dev/(tcp|udp)/([^/\s]+)/(\d+)")
# a reverse shell is an INTERACTIVE shell wired to the socket; `echo > /dev/tcp/h/443`
# alone is a connectivity check
REVERSE_SHELL = re.compile(r"\b(bash|sh|zsh)\s+-i\b.*/dev/(tcp|udp)/|/dev/(tcp|udp)/.*\b(bash|sh|zsh)\s+-i\b")
SEND_FLAGS = re.compile(r"(\s-X\s*(POST|PUT|PATCH)\b|\s(-d|--data\S*|-F|--form|-T|--upload-file)\s)", re.I)
URL = re.compile(r"(?:https?|ftp)://[^\s'\"|;)]+")
IP = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
ENDPOINT_STOP = {"api", "www", "html", "htm", "php", "json", "raw", "public", "bin", "exe", "index"}


@dataclass
class _Phrase:
    text: str
    priority: int
    net_host: str = ""     # set on phrases that make a network call, to fold connects into
    failed: bool = False


def _short(path: str) -> str:
    """Readable path: ~ for /root, 'its skill folder' for the skill's own files."""
    for p in SKILL_PREFIXES:
        if path == p or path.startswith(p.rstrip("/") + "/"):
            rest = path[len(p):].lstrip("/")
            return f"{rest} in its skill folder" if rest else "its skill folder"
    return path.replace("/root/", "~/", 1) if path.startswith("/root/") else path


def _area(path: str) -> str:
    """Folder that reads/writes are grouped under: the project under /workspace, else the parent."""
    parts = PurePosixPath(path).parts
    if len(parts) > 3 and parts[1] in ("workspace", "root", "home"):
        return _short("/" + "/".join(parts[1:3]))
    return _short(str(PurePosixPath(path).parent))


def _in_skill(path: str) -> bool:
    return any(path == p or path.startswith(p.rstrip("/") + "/") for p in SKILL_PREFIXES)


def _host(url_or_host: str) -> str:
    h = urlparse(url_or_host).hostname if "://" in url_or_host else url_or_host.split("/")[0].split(":")[0]
    return (h or "").lower()


def _where(host: str) -> str:
    return f"raw IP address {host}" if IP.match(host) else host


def _endpoint_words(url: str, limit: int = 4) -> str:
    """The URL path as plain words ("/v1/rank/users" -> "rank users"): which API was
    called is behaviour, and it shares vocabulary with the description. Version
    segments, ids and file extensions carry no meaning and are dropped."""
    words = [w.lower() for w in re.split(r"[/_.\-]+", urlparse(url).path)
             if len(w) >= 3 and w.isalpha() and w.lower() not in ENDPOINT_STOP]
    return " ".join(list(dict.fromkeys(words))[:limit])


def _program(cmd: str) -> tuple[str, list[str]]:
    """Program name and arguments, skipping wrappers like `timeout 20` and `VAR=x`."""
    toks = cmd.split()
    while toks and (toks[0] in WRAPPERS or "=" in toks[0] or re.fullmatch(r"\d+[smh]?", toks[0])):
        toks = toks[1:]
    return (PurePosixPath(toks[0]).name if toks else ""), toks[1:]


def _describe_exec(cmd: str) -> _Phrase | None:
    """One process_exec -> what it does, or None for plumbing whose effect shows elsewhere."""
    prog, args = _program(cmd)
    a = " ".join(args)
    if m := DEV_TCP.search(cmd):
        if REVERSE_SHELL.search(cmd):
            return _Phrase(f"opens a reverse shell connection to {m.group(2)}:{m.group(3)}", HIGH, m.group(2))
        return _Phrase(f"opens a raw network connection to {m.group(2)}:{m.group(3)}", MID, m.group(2))
    if MINERS.search(cmd):
        return _Phrase("runs a cryptocurrency miner", HIGH)
    if prog in ("sudo", "su"):
        inner = _describe_exec(a) if prog == "sudo" and a else None
        return _Phrase("runs a command as administrator" + (f" that {inner.text}" if inner else ""), HIGH)
    if prog in ("curl", "wget", "http", "https", "aria2c"):
        url = URL.search(cmd)
        host = _host(url.group(0)) if url else next((_host(t) for t in args if "." in t and not t.startswith("-")), "")
        if not host:
            return _Phrase("makes a web request", MID)
        what = _endpoint_words(url.group(0)) if url else ""
        where = _where(host) + (f" ({what})" if what else "")
        if SEND_FLAGS.search(f" {a} "):
            return _Phrase(f"sends data to {where}", HIGH, host)
        return _Phrase(f"downloads from {where}", HIGH if IP.match(host) else MID, host)
    if prog in ("nc", "ncat", "netcat", "socat", "telnet"):
        host = next((t for t in args if not t.startswith("-")), "")
        return _Phrase(f"opens a raw network connection to {host}".strip(), HIGH, _host(host))
    if prog in ("ssh", "scp", "rsync", "sftp"):
        host = next((t.split("@")[-1].split(":")[0] for t in args if "@" in t or ":" in t), "a remote host")
        return _Phrase(f"connects to {host} over SSH", HIGH, host)
    if prog == "base64":
        return _Phrase("decodes base64-encoded data" if re.search(r"(^|\s)(-d|-D|--decode)\b", a)
                       else "encodes data as base64", MID)
    if prog == "chmod":
        target = PurePosixPath(args[-1]).name if args else "a file"
        return _Phrase(f"makes {target} executable" if re.search(r"\+x|\b[0-7]?[157][0-7]{2}\b", a)
                       else "changes file permissions", MID)
    if prog == "crontab":
        return _Phrase("schedules a recurring cron job", HIGH)
    if prog in ("useradd", "usermod", "passwd", "chpasswd", "chown", "visudo"):
        return _Phrase("changes user accounts or file ownership", HIGH)
    if prog in ("systemctl", "service"):
        return _Phrase("manages system services", HIGH)
    if prog in ("kill", "pkill", "killall"):
        return _Phrase("stops other processes", MID)
    if prog in ("openssl", "gpg"):
        return _Phrase("encrypts or decrypts data", MID)
    if prog in ("env", "printenv"):
        return _Phrase("reads environment variables", MID)
    if prog in INSTALLERS or (prog in INTERPRETERS and args[:2] == ["-m", "pip"]):
        rest = args[2:] if prog in INTERPRETERS else args
        if rest and rest[0] in ("install", "add", "i"):
            pkgs = [t for t in rest[1:] if not t.startswith("-")][:4]
            return _Phrase("installs packages" + (f" {', '.join(pkgs)}" if pkgs else ""), MID)
        return _Phrase(f"uses the {prog} package manager", LOW)
    if prog == "npx":
        return _Phrase(f"runs package {args[0]} with npx" if args else "runs a package with npx", MID)
    if prog == "git":
        url = URL.search(cmd)
        if args[:1] == ["clone"] and url:
            return _Phrase(f"clones a repository from {_host(url.group(0))}", MID, _host(url.group(0)))
        return _Phrase(f"uses git {args[0]}" if args else "uses git", LOW)
    if prog in INTERPRETERS:
        lang = INTERPRETERS[prog]
        script = next((t for t in args if not t.startswith("-")), "")
        if not args or args[0] in ("-c", "-e", "-") or not script:
            return _Phrase("starts a shell" if lang == "shell" and not args else f"runs inline {lang} code", MID)
        if args[0] == "-m":
            return _Phrase(f"runs {lang} module {args[1] if len(args) > 1 else ''}".strip(), MID)
        name = PurePosixPath(script).name
        if name in INSTALLERS or name == "npx":
            return None                               # `node .../npm`: the npm process is described
        return _Phrase(f"runs {lang} script {name}", MID)
    if prog.endswith(SCRIPT_EXT) or cmd.startswith("./"):
        return _Phrase(f"runs script {prog}", MID)
    if prog in CLOUD_CLIS:
        return _Phrase(f"uses the {prog} command-line tool", MID)
    if prog in ARCHIVE:
        return _Phrase("archives or extracts files", MID)
    if prog in SYSINFO:
        return _Phrase("collects system information", MID)
    if prog in LISTING:
        return _Phrase("lists files", LOW)
    if prog in PLUMBING or not prog:
        return None
    return _Phrase(f"runs program {prog}", MID)


def _phrases(trace: list[dict]) -> list[_Phrase]:
    out: list[_Phrase] = []
    groups: dict[tuple[str, str], _Phrase] = {}   # (verb, folder) -> phrase, filled in at the end
    counts: dict[tuple[str, str], int] = {}

    def grouped(verb: str, path: str) -> _Phrase | None:
        key = (verb, _area(path))
        counts[key] = counts.get(key, 0) + 1
        if key in groups:
            return None
        groups[key] = _Phrase("", MID)
        return groups[key]

    steps_with_exec = {a.get("step") for a in trace if a["action"] == "process_exec"}
    last_prog, last_net = "", None
    for a in trace:
        act, tgt, ok = a["action"], a.get("target", ""), a.get("status", "ok") == "ok"
        p = None
        if act in ("skill_load", "subagent"):
            continue                                  # harness bookkeeping, not behaviour
        if act == "command":
            if a.get("step") in steps_with_exec:
                continue                              # its processes are described instead
            p = _describe_exec(tgt)
        elif act == "process_exec":
            last_prog, last_net = _program(tgt)[0], None   # later connects belong to this process
            p = _describe_exec(tgt)
        elif act == "file_read":
            if TOOL_CONFIG_READS.search(tgt) or (tgt.endswith("/.netrc") and last_prog in NETRC_READERS):
                continue
            if SENSITIVE_RE.search(tgt):
                p = _Phrase(f"reads credential file {_short(tgt)}" + ("" if ok else " (not found)"), HIGH)
            elif _in_skill(tgt):
                p = _Phrase("reads its own skill files", LOW)
            elif tgt.startswith("/workspace/.opencode"):
                p = _Phrase("reads the agent's configuration", LOW)
            elif tgt in ("/", "/workspace", "/tmp", "/root", "/etc"):
                p = _Phrase("lists files", LOW)
            else:
                p = grouped("reads", tgt)
        elif act == "file_write":
            if PERSISTENCE_RE.search(tgt):
                p = _Phrase(f"modifies startup or system file {_short(tgt)}", HIGH)
            elif _in_skill(tgt) or tgt.startswith("/tmp/"):
                p = _Phrase(f"writes temporary file {PurePosixPath(tgt).name}", LOW)
            else:
                p = grouped("writes", tgt)
        elif act == "file_delete":
            p = grouped("deletes", tgt)
        elif act == "network_connect":
            ip, _, port = tgt.rpartition(":")
            if last_net is not None and (ip == SINKHOLE_IP or ip == last_net.net_host):
                last_net.failed = last_net.failed or not ok
                continue                              # already said by the command that connected
            if ip == SINKHOLE_IP:
                p = _Phrase(f"connects to an external server on port {port}", MID, ip, not ok)
            else:
                p = _Phrase(f"connects to raw IP address {ip} on port {port}", HIGH, ip, not ok)
        elif act == "dns_lookup":
            if last_net is not None and _host(tgt) == last_net.net_host:
                continue
            p = _Phrase(f"contacts domain {_host(tgt)}", MID, _host(tgt))
        elif act == "web_fetch":
            p = _Phrase(f"fetches web page {_host(tgt)}", MID, _host(tgt), not ok)
        elif act == "file_search":
            p = _Phrase("searches for files", LOW)
        else:
            p = _Phrase(f"{act.replace('_', ' ')} {tgt}".strip(), LOW)
        if p is None:
            continue
        if p.net_host:
            last_net = p
        out.append(p)
    for (verb, d), p in groups.items():
        n = counts[(verb, d)]
        p.text = f"{verb} {n} files in {d}" if n > 1 else f"{verb} a file in {d}"
        p.priority = HIGH if verb == "deletes" and n >= 10 else MID
    return out


def trace_to_flat_text(trace: list[dict]) -> str:
    """The NON-enriched baseline: each action as "<action> <target>", in order.

    No templates and no naming of sensitive actions; the encoder sees the raw
    trace vocabulary. Consecutive duplicates are collapsed so repeated reads do
    not use up the encoder's token limit. The enriched converter below is
    measured against this (Experiment 2, enrichment ablation).

    skill_load is dropped, as in the enriched text: its target is the skill's
    NAME, which resembles the description and would score consistency for free.
    """
    parts = []
    for a in trace:
        if a["action"] in ("skill_load", "subagent"):
            continue
        text = f"{a['action'].replace('_', ' ')} {a['target']}".strip()
        if a.get("status", "ok") != "ok":
            text += f" ({a['status']})"
        if not parts or parts[-1] != text:
            parts.append(text)
    return "; ".join(parts) or "nothing"


def trace_to_enriched_text(trace: list[dict], max_chars: int = 900) -> str:
    """Convert a raw action trace into enriched descriptive text.

    Example output: "runs Python script game_launcher.py, then downloads from
    raw IP address 45.88.180.54 (connection failed), then makes node
    executable, then modifies startup or system file ~/.bashrc"

    max_chars keeps the text inside the encoder's 256-token window (this text
    averages ~4.5 characters a token; long hostnames make words a poor unit);
    LOW then MEDIUM phrases go first.
    """
    seen, phrases = set(), []
    for p in _phrases(trace):
        text = p.text + (" (connection failed)" if p.failed else "")
        if text not in seen:
            seen.add(text)
            phrases.append((text, p.priority))
    for drop in (LOW, MID):
        if sum(len(t) + 7 for t, _ in phrases) <= max_chars:
            break
        phrases = [(t, pr) for t, pr in phrases if pr != drop]
    used, kept = 0, []
    for t, _ in phrases:                              # still too long: keep the start
        if used + len(t) + 7 > max_chars and kept:
            break
        kept.append(t)
        used += len(t) + 7                            # 7 = len(", then ")
    if not kept:
        return "Does nothing observable"
    text = ", then ".join(kept)
    return text[0].upper() + text[1:]
