import re
import divergence.preprocessing.normalise_trace as nt
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

