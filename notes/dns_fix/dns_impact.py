"""Impact of reading DNS names from resolver replies, on the 308 dataset runs (no project files changed)."""
import collections, json, re, sys
from pathlib import Path
sys.path.insert(0, ".")
import divergence.preprocessing.normalise_trace as nt
from divergence.preprocessing.structural_flags import compute_structural_flags

_ESC = re.compile(rb'\\(x[0-9a-fA-F]{2}|[0-7]{1,3}|.)')
_SIMPLE = {b"n": 10, b"r": 13, b"t": 9, b"v": 11, b"f": 12, b"a": 7, b"b": 8, b"e": 27}

def unescape(s: str) -> bytes:
    def rep(m):
        e = m.group(1)
        if e[:1] == b"x": return bytes([int(e[1:], 16)])
        if e[:1].isdigit(): return bytes([int(e, 8) & 0xFF])
        return bytes([_SIMPLE.get(e, e[0])])
    return _ESC.sub(rep, s.encode("latin-1", "replace"))

def qname(payload: bytes):
    if len(payload) < 13: return None
    i, labels = 12, []
    while i < len(payload):
        n = payload[i]
        if n == 0: break
        if n > 63 or i + 1 + n > len(payload): return None
        labels.append(payload[i+1:i+1+n].decode("ascii", "replace")); i += 1 + n
    else:
        return None
    name = ".".join(labels).lower()
    return name if nt.re.fullmatch(r"[a-z0-9_-]+(\.[a-z0-9_-]+)+", name) else None

def dns_names(n):
    if n.get("port") != 53 or n.get("address") not in nt.SANDBOX_DNS: return []
    if n.get("syscall") not in ("recvfrom", "recvmsg", "sendto", "sendmsg", "sendmmsg"): return []
    m = nt._QUOTED.search(n.get("args", ""))
    q = qname(unescape(m.group(1))) if m else None
    return [q] if q else []

orig = nt._os_events
def patched(result, **kw):
    yield from orig(result, **kw)
    for n in result.get("network_events") or []:
        for d in dns_names(n):
            yield n.get("pid"), "dns_lookup", d, "ok"

MODE_DIR = {"agent": "batch_out", "direct": "direct_out", "instructed": "instructed_out"}
rows = [json.loads(l) for l in open("data/processed/labelled_dataset.jsonl")]
stats = collections.Counter(); examples = []
for r in rows:
    res = json.loads((Path("data/raw/traces") / MODE_DIR[r["mode"]] / "results" / f"{r['sample_id']}.json").read_text())
    nt._os_events = orig; old = nt.normalise(res)
    nt._os_events = patched; new = nt.normalise(res)
    nt._os_events = orig
    assert [a for a in old] == [a for a in old]
    if old != new:
        stats[("trace changed", r["mode"], r["label"])] += 1
        added = sorted({a["target"] for a in new if a["action"] == "dns_lookup"} - {a["target"] for a in old if a["action"] == "dns_lookup"})
        fo = compute_structural_flags(r["description"], old).flag_unmentioned_domain
        fn = compute_structural_flags(r["description"], new).flag_unmentioned_domain
        if fo != fn:
            stats[("domain flag changed", r["mode"], "POS" if r["label"] else "NEG", f"{fo}->{fn}")] += 1
            examples.append((r["sample_id"], r["mode"], r["label"], added[:5]))
        elif len(examples) < 0: pass
        stats["_added_names"] += len(added)
        for a in added: stats[("name", a)] += 1
# also: does the stored dataset trace equal old normalise? (sanity)
same = sum(1 for r in rows if nt.normalise(json.loads((Path("data/raw/traces")/MODE_DIR[r["mode"]]/"results"/f"{r['sample_id']}.json").read_text())) == r["trace"])
print("stored traces reproduced by current normalise():", same, "/", len(rows))
for k, v in sorted(((k, v) for k, v in stats.items() if k[0] != "name"), key=str): print(k, v)
print("most common added names:", [(k[1], v) for k, v in stats.most_common() if k[0] == "name"][:25])
print("runs whose domain flag flips:")
for e in examples: print(" ", e)
