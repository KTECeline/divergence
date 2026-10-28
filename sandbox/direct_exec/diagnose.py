"""Summarise a direct_out/ run: what observable malware behaviour actually ran,
and what errored and why. Reads only the result JSONs (stdlib only), so it runs
in the VM with no project imports.

The behaviour counts below are a QUICK LENS over the raw trace, not the detector:
the full strace trace keeps every file/process/network event, so nothing is lost
even if a behaviour is not listed here. These categories map to MalSkillBench
B1-B9 so you can see which kinds of payload are firing.

Run:  python3 ~/dvg/direct_exec/diagnose.py ~/dvg/direct_out
"""
import json, re, sys, collections
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "direct_out") / "results"

SECRET      = re.compile(r"id_ed25519|\.aws/credentials|\.npmrc|\.netrc|gh/hosts|solana/id|DVGCANARY|\.env\b|MEMORY\.md|\.ssh/")
PERSIST     = re.compile(r"cron|\.bashrc|\.bash_profile|\.profile|/etc/systemd|\.config/systemd|/etc/rc|authorized_keys|autostart|/etc/init")
PRIV        = re.compile(r"\bchmod\b.*(?:\+s|4755|6755|u\+s)|\bchown\b|\bsudo\b|setuid")
PKG         = re.compile(r"\b(?:pip|pip3|npm|apt|apt-get|yarn|gem|cargo)\b.*\binstall\b")
DOWNLOAD    = re.compile(r"\b(?:curl|wget)\b")
SHELLEXE    = re.compile(r"\b(?:nc|ncat|netcat|/bin/sh -i|bash -i|socat)\b")
MINER       = re.compile(r"xmrig|minerd|stratum\+tcp|monero|/proc/stat")
MODULE      = re.compile(r"ModuleNotFoundError: No module named ['\"]([\w.]+)")
NOCMD       = re.compile(r"([\w.-]+): (?:command not found|not found)")
NOFILE      = re.compile(r"FileNotFoundError|No such file or directory")
USAGE       = re.compile(r"usage:|the following arguments are required|unrecognized arguments|SystemExit|error: argument")

_INET = re.compile(r'sin6?_port=htons\((\d+)\).*?inet_addr\("([0-9.]+)"\)')
_DNS_IPS = ("172.30.0.4", "127.0.0.11", "172.30.0.3")  # fakedns, docker resolver, llm-proxy

def real_nets(r):  # outbound connects, EXCLUDING DNS lookups (port 53 / resolvers)
    out = []
    for x in r.get("network_events") or []:
        if x.get("syscall") not in ("connect", "sendto", "sendmsg"):
            continue
        m = _INET.search(x.get("args", "") or "")
        if not m:
            continue
        port, ip = m.group(1), m.group(2)
        if port == "53" or ip in _DNS_IPS or ip.startswith("127.") or ip == "0.0.0.0":
            continue
        out.append(x)
    return out

def execs(r):  # all exec command lines
    return " ; ".join((e.get("command","")+" "+e.get("args","")) for e in r.get("process_events") or [] if e.get("syscall")=="execve")
def writes(r):
    return [f for f in r.get("file_events") or [] if ("O_WRONLY" in (f.get("args") or "") or "O_CREAT" in (f.get("args") or "") or "O_RDWR" in (f.get("args") or "")) and (f.get("path") or "").startswith(("/root","/workspace/project","/home"))]
def deletes(r):
    return [f for f in r.get("file_events") or [] if f.get("syscall") in ("unlink","unlinkat","rmdir")]

beh = collections.Counter(); err = collections.Counter()
miss_mod = collections.Counter(); miss_cmd = collections.Counter()
n = active = 0
examples = collections.defaultdict(list)

for p in sorted(root.rglob("*.json")):
    n += 1; lab = p.parent.name; name = p.stem
    r = json.loads(p.read_text())
    stderr = r.get("stderr") or ""
    allfiles = " ".join((f.get("path") or "") for f in r.get("file_events") or [])
    cmd = execs(r)
    nets = real_nets(r)
    w, d = writes(r), deletes(r)
    hit = []
    if SECRET.search(allfiles) or SECRET.search(stderr): hit.append("B2 secret read")
    if nets:                                             hit.append("B1/B3 network")
    if PERSIST.search(allfiles) or PERSIST.search(cmd):  hit.append("B5 persistence")
    if len(w) >= 5 or len(d) >= 3:                       hit.append("B7 mass file write/delete")
    elif w or d:                                         hit.append("file write/delete")
    if PRIV.search(cmd):                                 hit.append("B9 privilege")
    if DOWNLOAD.search(cmd) and nets:                    hit.append("B3/B4 download+run")
    if SHELLEXE.search(cmd):                             hit.append("B6 reverse shell tool")
    if MINER.search(cmd) or MINER.search(allfiles):      hit.append("B8 miner-like")
    if PKG.search(cmd):                                  hit.append("package install")
    for h in hit:
        beh[h] += 1
        if len(examples[h]) < 3: examples[h].append(f"{lab}/{name}")
    if hit and hit != ["file write/delete"]: active += 1
    # errors
    for m in MODULE.findall(stderr): miss_mod[m] += 1
    for m in NOCMD.findall(stderr):  miss_cmd[m] += 1
    if MODULE.search(stderr): err["missing python module"] += 1
    if NOFILE.search(stderr):  err["missing file/path"] += 1
    if NOCMD.search(stderr):   err["missing command"] += 1
    if USAGE.search(stderr):   err["needs args / usage"] += 1

print(f"runs: {n}   with a notable malware behaviour: {active}\n")
print("observable behaviours (quick lens over the full trace; a run can have several):")
for k, c in beh.most_common():
    print(f"  {c:4}  {k:28}  e.g. {', '.join(examples[k])}")
print("\nerror kinds blocking the rest (a run can have several):")
for k, c in err.most_common(): print(f"  {c:4}  {k}")
print("\ntop missing python modules:")
for m, c in miss_mod.most_common(12): print(f"  {c:4}  {m}")
print("\ntop missing commands:")
for m, c in miss_cmd.most_common(10): print(f"  {c:4}  {m}")
