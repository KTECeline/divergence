"""Baseline: AGT-only (non-trained). Build order item 11.

Decision from AGT's own governance signals alone, with no Divergence
semantic-consistency layer.

AGT 4.1.0 has no built-in check of a skill against its description: its audit
log records tool calls, and its policy engine allows or denies them by rules
the operator writes. So this baseline is the strongest rule an operator could
write over AGT's audit log alone: escalate any run whose TOOL CALLS (no OS-level
events, no description) show network contact, credential access or a risky
action type. It stands in for "AGT as deployed"; it is not AGT's own output.
"""

from src.evaluator.agt_adapter import agt_visible
from src.preprocessing.structural_flags import compute_structural_flags


def score(sample) -> int:
    return sum(compute_structural_flags("", agt_visible(sample["trace"])).as_list())


def predict(sample) -> int:
    return int(score(sample) > 0)
