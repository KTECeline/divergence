"""Experiment 5: inconsistency vs maliciousness controls. Build order item 15.

Tests whether Divergence detects intent-behaviour divergence or just
maliciousness. Three parts, all on the held-out test split:

  5a. Proxy validity — share of hand-labelled malicious samples whose
      description does NOT disclose the harmful behaviour.
  5b. Swapped description (benign, inconsistent) — expect FLAG.
  5c. Disclosed payload (malicious, consistent) — expect ALLOW.

If 5c is mostly flagged, the model is detecting maliciousness, and claims in
the report must be narrowed accordingly. Writes results/exp5_controls.csv.
"""


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
