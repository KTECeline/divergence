# DNS capture gap: measurement and fix (2026-11-17)

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

The two measurement scripts ran against the normaliser BEFORE the fix (they patch it at run
time); now that the fix is applied they compare the fixed normaliser with itself, so re-running
them shows no change. The fix itself was checked to give the same 170 traces and 17 flips.

**Step 1 (code fix) applied 2026-11-17**: `_resolver_dns_names` / `dns_question` in
`divergence/preprocessing/normalise_trace.py`, 4 new tests. Until step 2 of REDO.md is run, the
stored dataset traces are the OLD ones (`check_dataset.py` reports 170 stale traces; expected).

Decision: full redo (fix `normalise_trace._os_events`, regenerate the traces, retrain
the encoder and calibrator, rerun the experiments, re-upload the model and move the pin).
