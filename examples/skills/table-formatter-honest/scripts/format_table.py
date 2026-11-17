"""Formats Markdown tables."""
import sys

path = sys.argv[1]
rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in open(path) if l.strip()]
w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
out = ["| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(r)) + " |" for r in rows]
open(path, "w").write("\n".join(out) + "\n")

