"""Schema for a single skill sample parsed from MalSkillBench.

Build order item 2 (alongside loader.py). Adjust fields once the raw
MalSkillBench format has been inspected.
"""

from dataclasses import dataclass, field


@dataclass
class SkillSample:
    """One skill: its declared description, observed action trace, and labels."""

    sample_id: str
    description: str
    trace: list[dict]  # raw action trace events (format TBD from dataset inspection)
    label: int  # 1 = malicious/inconsistent, 0 = benign/consistent

    # MalSkillBench three-dimensional taxonomy tags
    attack_vector: str | None = None  # Code Injection / Prompt Injection / Mixed
    behaviour_class: str | None = None
    insertion_strategy: str | None = None

    metadata: dict = field(default_factory=dict)
