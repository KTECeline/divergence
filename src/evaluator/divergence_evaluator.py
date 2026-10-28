"""DivergenceEvaluator — the AGT-pattern evaluator wrapping the full pipeline.

Build order item 10. Follows the shape of AGT's own PromptDefenseEvaluator
(`agent_compliance.prompt_defense`, AGT 4.1.0): a deterministic evaluator with
`evaluate()` returning a report object that has `to_dict()` / `to_json()`.
Cite this precedent in report section 2.4.3.4:

    evaluator = DivergenceEvaluator()
    result = evaluator.evaluate(skill_description, agt_audit_log)
    result.consistency_score  # e.g. 0.31
    result.structural_flags   # e.g. ['flag_unmentioned_domain']
    result.verdict            # "ALLOW" / "FLAG"
    result.reasoning          # human-readable explanation

Divergence does not make AGT's policy decision. `to_agt_evidence()` gives the
result as evidence to attach to that decision, with a suggested AGT 4.1.0
`PolicyDecision` value: FLAG -> "escalate" (route to a human before install),
ALLOW -> "allow".

Everything is fixed before evaluation: the fine-tuned encoder (notebook 05),
the calibration weights (notebook 06) and the 0.5 cut-off. Nothing here is
fitted.
"""

import json
from dataclasses import asdict, dataclass, field

import numpy as np

from src.calibration.logistic_calibrator import FLAG_THRESHOLD, LogisticCalibrator, feature_row
from src.config import CALIBRATION_MODEL_PATH, FINETUNED_EMBEDDING_DIR, VERDICT_ALLOW, VERDICT_FLAG
from src.embedding.encoder import Encoder
from src.embedding.similarity import consistency_scores
from src.evaluator.agt_adapter import to_divergence_trace
from src.preprocessing.structural_flags import StructuralFlags, compute_structural_flags
from src.preprocessing.trace_to_text import trace_to_enriched_text

EVALUATOR_NAME = "divergence"
EVALUATOR_VERSION = "1.0"
EMPTY_TRACE_TEXT = "Does nothing observable"
AGT_DECISION = {VERDICT_FLAG: "escalate", VERDICT_ALLOW: "allow"}  # agent_os.base_agent.PolicyDecision values


@dataclass
class DivergenceResult:
    consistency_score: float
    structural_flags: list[str]
    verdict: str  # config.VERDICT_ALLOW or config.VERDICT_FLAG
    reasoning: str
    probability: float = 0.0  # calibrated probability that behaviour diverges from the description
    flag_evidence: dict = field(default_factory=dict)  # why each flag fired
    trace_text: str = ""  # the enriched text the score was computed on

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        """Deterministic JSON (sorted keys), like PromptDefenseReport.to_json()."""
        return json.dumps(self.to_dict(), sort_keys=True)

    def to_agt_evidence(self) -> dict:
        """The result as evidence for AGT's policy decision (Divergence does not decide it)."""
        return {"evaluator": EVALUATOR_NAME, "version": EVALUATOR_VERSION,
                "suggested_policy_decision": AGT_DECISION[self.verdict], **self.to_dict()}


def _reasoning(probability: float, score: float, flags: StructuralFlags, text: str,
               weights: dict[str, float]) -> str:
    """Plain-language explanation built from the same numbers that made the verdict."""
    verdict = VERDICT_FLAG if probability >= FLAG_THRESHOLD else VERDICT_ALLOW
    lines = [f"{verdict}: estimated {probability:.0%} probability that the observed behaviour diverges "
             f"from the description (FLAG at {FLAG_THRESHOLD:.0%} or more).",
             f"Semantic consistency between description and behaviour: {score:.2f} (0 = unrelated, 1 = same meaning)."]
    ev = flags.evidence
    if flags.flag_unmentioned_domain:
        lines.append(f"Contacted host(s) the description never names: {', '.join(ev['unmentioned_hosts'])} "
                     f"(weight {weights['flag_unmentioned_domain']:+.2f}).")
    if flags.flag_credential_access:
        lines.append(f"Read credential file(s) although the description does not mention credentials: "
                     f"{', '.join(ev['credential_reads'])} (weight {weights['flag_credential_access']:+.2f}).")
    if flags.flag_undeclared_action_type:
        lines.append(f"Performed action type(s) the description has no words for: "
                     f"{', '.join(ev['undeclared_action_types'])} (weight {weights['flag_undeclared_action_type']:+.2f}).")
    if not flags.raised():
        lines.append("No structural red flag fired.")
    lines.append("The run produced no observable actions." if text == EMPTY_TRACE_TEXT
                 else f"Observed: {text[:240]}{'...' if len(text) > 240 else ''}")
    return "\n".join(lines)


class DivergenceEvaluator:
    """Wraps pipeline Steps 1-6: encode description, enrich + encode trace,
    cosine similarity, structural red-flag rules, logistic calibration.

    Loads the fine-tuned embedding model and calibration model once at
    construction; both are reused for every skill scanned afterward.
    `encoder` / `calibrator` can be passed in (tests, ablations).
    """

    def __init__(self, encoder: Encoder | None = None, calibrator: LogisticCalibrator | None = None):
        self.encoder = encoder or Encoder(str(FINETUNED_EMBEDDING_DIR))
        self.calibrator = calibrator or LogisticCalibrator.load(CALIBRATION_MODEL_PATH)
        self.weights = self.calibrator.coefficients()

    def evaluate(self, skill_description: str, audit_log: list,
                 os_events: list[dict] | None = None) -> DivergenceResult:
        """Score one skill run.

        audit_log: AGT AuditEntry objects/dicts, or an already-normalised
        Divergence trace. os_events: the sandbox's OS-level events per AGT entry
        (see agt_adapter); without them only AGT-visible actions are scored.
        """
        return self.evaluate_batch([(skill_description, audit_log, os_events)])[0]

    def evaluate_batch(self, runs: list[tuple]) -> list[DivergenceResult]:
        """evaluate() for many (description, audit_log[, os_events]) runs, encoding in one pass."""
        descriptions = [r[0] for r in runs]
        traces = [to_divergence_trace(r[1], r[2] if len(r) > 2 else None) for r in runs]
        texts = [trace_to_enriched_text(t) for t in traces]
        scores = consistency_scores(self.encoder.encode(descriptions), self.encoder.encode(texts))
        flags = [compute_structural_flags(d, t) for d, t in zip(descriptions, traces)]
        probs = self.calibrator.predict_proba(np.array([feature_row(s, f) for s, f in zip(scores, flags)]))
        return [DivergenceResult(consistency_score=round(float(s), 4), structural_flags=f.raised(),
                                 verdict=VERDICT_FLAG if p >= FLAG_THRESHOLD else VERDICT_ALLOW,
                                 reasoning=_reasoning(float(p), float(s), f, t, self.weights),
                                 probability=round(float(p), 4), flag_evidence=f.evidence, trace_text=t)
                for s, f, p, t in zip(scores, flags, probs, texts)]
