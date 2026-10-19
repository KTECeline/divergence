"""Experiment 6: held-out category generalisation. Build order item 16.

Tests whether the model learns divergence as a concept or memorises known
attack vocabulary. Two settings:

  6a. Leave-one-behaviour-class-out — one fold per behaviour class; train
      without that class, test only on it.
  6b. Cross attack vector — train on Code Injection, test on Prompt
      Injection, and the reverse. Mixed is excluded from both sides, since
      it contains both vectors and would leak the held-out one.

Folds must still respect the group-aware split from splitter.py. Writes
results/exp6_holdout.csv (one row per fold, plus the random-split score for
comparison).
"""


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
