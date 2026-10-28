"""Baseline: text-only. Build order item 11.

Uses the declared skill description alone, ignoring observed behaviour. A
description cannot be judged "consistent" without behaviour, so this baseline
is necessarily trained: TF-IDF words + logistic regression, fitted on the
fine-tune and calibration splits (the same labelled data Divergence used).
It measures how much of the label can be guessed from description wording
alone (e.g. generator style, attack-themed skill names). If it scores well,
the labels leak through the description.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from src.config import RANDOM_SEED


class TextOnlyBaseline:
    def __init__(self):
        self.model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                                   LogisticRegression(max_iter=1000, random_state=RANDOM_SEED))

    def fit(self, samples) -> "TextOnlyBaseline":
        self.model.fit([s["description"] for s in samples], [s["label"] for s in samples])
        return self

    def predict_proba(self, samples) -> np.ndarray:
        return self.model.predict_proba([s["description"] for s in samples])[:, 1]

    def predict(self, sample) -> int:
        return int(self.predict_proba([sample])[0] >= 0.5)
