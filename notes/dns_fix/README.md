# DNS capture gap: measurement (2026-11-17), fix not yet applied

The MalSkillBench runner reads DNS names only from `sendto` to port 53 and from the
arguments of `curl`/`wget`/`ping`/`dig`/`host`/`nslookup`. glibc's resolver (used by Python,
and so by most in-process network code) sends queries with `sendmmsg`, so a skill that
uploads from inside its own code loses the hostname, and `flag_unmentioned_domain` never fires.

Proposed fix: decode the question name from port-53 `recvfrom` payloads exchanged with the
sandbox resolver (`SANDBOX_DNS`) and emit `dns_lookup` actions (`dns_impact_lib.py`).

Measured on the 308 dataset runs, nothing in the project changed:

| | Result |
|---|---|
| Traces that change | 170 / 308 |
| Domain flag off -> on | 17 malicious runs (all direct mode), 0 benign |
| Held-out test, current model, no retrain | TP 41 -> 44, FN 14 -> 11, FP 6 -> 6 |
| Calibration split | FN 8 -> 3, FP 4 -> 4 |
| Fine-tune split | FN 24 -> 15, FP 11 -> 11 |

Run from the repo root: `.venv/bin/python notes/dns_fix/dns_impact.py` and
`.venv/bin/python notes/dns_fix/dns_verdicts.py notes/dns_fix`.

Decision: full redo later (fix `normalise_trace._os_events`, regenerate the traces, retrain
the encoder and calibrator, rerun the experiments, re-upload the model and move the pin).
