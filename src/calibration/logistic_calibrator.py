"""Logistic regression calibration layer (pipeline Step 6).

Build order item 9. Fit on the calibration split:
    logistic_regression([similarity, flag1, flag2, flag3])
    -> probability-of-suspicious -> ALLOW / FLAG verdict
Saved to / loaded from models/calibration_model.json: plain weights, not a pickle,
because the evaluator loads it inside the AGT deployment and unpickling a file
can run arbitrary code.

The similarity scores it is fitted on must come from the fine-tuned encoder,
which never saw the calibration split; scores on data the encoder trained on
are too clean, and the weights learned from them would not hold on new skills.
The FLAG cut-off (0.5) is fixed in advance, not tuned.
"""

import json

import numpy as np
from sklearn.linear_model import LogisticRegression

from src.config import CALIBRATION_MODEL_PATH, RANDOM_SEED
from src.preprocessing.structural_flags import StructuralFlags

FLAG_THRESHOLD = 0.5
FEATURES = ("consistency_score",) + StructuralFlags.NAMES


def feature_row(consistency_score: float, flags: StructuralFlags) -> list[float]:
    return [float(consistency_score)] + [float(f) for f in flags.as_list()]


class LogisticCalibrator:
    def __init__(self, feature_names: tuple[str, ...] = FEATURES, C: float = 1.0):
        self.feature_names = tuple(feature_names)
        self.model = LogisticRegression(C=C, max_iter=1000, random_state=RANDOM_SEED)

    def fit(self, features, labels) -> None:
        self.model.fit(np.asarray(features, dtype=float), np.asarray(labels))

    def predict_proba(self, features) -> np.ndarray:
        """Probability that each skill run is suspicious (inconsistent)."""
        X = np.atleast_2d(np.asarray(features, dtype=float))
        return self.model.predict_proba(X)[:, 1]

    def coefficients(self) -> dict[str, float]:
        """Learned weight per feature (log-odds per unit); negative = pushes towards ALLOW."""
        return {"intercept": float(self.model.intercept_[0]),
                **dict(zip(self.feature_names, map(float, self.model.coef_[0])))}

    def save(self, path=CALIBRATION_MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"feature_names": list(self.feature_names), "threshold": FLAG_THRESHOLD,
                                    "intercept": float(self.model.intercept_[0]),
                                    "coef": [float(c) for c in self.model.coef_[0]]}, indent=1))

    @classmethod
    def load(cls, path=CALIBRATION_MODEL_PATH) -> "LogisticCalibrator":
        d = json.loads(path.read_text())
        cal = cls(tuple(d["feature_names"]))
        cal.model.classes_ = np.array([0, 1])
        cal.model.coef_ = np.array([d["coef"]])
        cal.model.intercept_ = np.array([d["intercept"]])
        return cal
