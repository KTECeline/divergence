"""Split MalSkillBench into fine-tune / calibration / held-out test splits.

Build order item 4. Splits must be strictly separated (no leakage):
fine-tuning, calibration, and evaluation each see disjoint samples.
Outputs finetune.jsonl, calibration.jsonl, held_out_test.jsonl to
data/processed/splits/.
"""

from src.data.schema import SkillSample


def make_splits(samples: list[SkillSample], seed: int) -> None:
    """Create and persist the three leakage-free splits."""
    raise NotImplementedError
