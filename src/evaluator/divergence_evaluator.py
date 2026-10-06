"""DivergenceEvaluator — the AGT-pattern evaluator wrapping the full pipeline.

Build order item 10. Follows the shape of AGT's own PromptDefenseEvaluator
(pre-policy evaluator returning a structured result object — cite this
precedent in report section 2.4.3.4):

    evaluator = DivergenceEvaluator()
    result = evaluator.evaluate(skill_description, agt_audit_log)
    result.consistency_score  # e.g. 0.31
    result.structural_flags   # e.g. ['flag_unmentioned_domain']
    result.verdict            # "ALLOW" / "FLAG"
    result.reasoning          # human-readable explanation
"""

from dataclasses import dataclass


@dataclass
class DivergenceResult:
    consistency_score: float
    structural_flags: list[str]
    verdict: str  # config.VERDICT_ALLOW or config.VERDICT_FLAG
    reasoning: str


class DivergenceEvaluator:
    """Wraps pipeline Steps 1-6: encode description, enrich + encode trace,
    cosine similarity, structural red-flag rules, logistic calibration.

    Loads the fine-tuned embedding model and calibration model once at
    construction; both are reused for every skill scanned afterward.
    """

    def __init__(self):
        raise NotImplementedError

    def evaluate(self, skill_description: str, audit_log: list[dict]) -> DivergenceResult:
        raise NotImplementedError
