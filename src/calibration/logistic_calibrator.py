"""Logistic regression calibration layer (pipeline Step 6).

Build order item 9. Fit on the calibration split:
    logistic_regression([similarity, flag1, flag2, flag3])
    -> probability-of-suspicious -> ALLOW / FLAG verdict
Saved to / loaded from models/calibration_model.pkl.
"""


class LogisticCalibrator:
    def fit(self, features, labels) -> None:
        raise NotImplementedError

    def predict_proba(self, features) -> float:
        """Probability that the skill is suspicious."""
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    @classmethod
    def load(cls) -> "LogisticCalibrator":
        raise NotImplementedError
