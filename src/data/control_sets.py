"""Build the control sets that separate inconsistency from maliciousness.

Used by Experiment 5. MalSkillBench labels skills malicious/benign, not
consistent/inconsistent, so these sets test which of the two the model is
actually detecting. Built from the held-out test split only, so no control
sample shares a source skill with the fine-tune or calibration splits.
Outputs go to data/processed/controls/.
"""

from src.data.schema import SkillSample


def build_proxy_labelling_sheet(samples: list[SkillSample], n: int, seed: int) -> None:
    """Sample n malicious skills into a CSV for hand-labelling.

    Columns: sample_id, attack_vector, behaviour_class, insertion_strategy,
    description, enriched_trace, discloses_harmful_behaviour (yes/partial/no),
    labeller_notes. Stratify by insertion strategy so every strategy is covered.
    Writes data/processed/controls/proxy_labelling_sheet.csv.
    """
    raise NotImplementedError


def build_swapped_description_set(samples: list[SkillSample], seed: int) -> list[SkillSample]:
    """Benign trace paired with a different benign skill's description.

    Inconsistent but not malicious — the model should flag these. Pick the
    swap partner from a different behaviour domain so the pair is clearly
    mismatched, not a near-synonym skill.
    """
    raise NotImplementedError


def build_disclosed_payload_set(samples: list[SkillSample]) -> list[SkillSample]:
    """Malicious trace paired with a description that honestly states the payload.

    Malicious but consistent — the model should score these as consistent.
    Rewritten descriptions are produced outside this code (by hand or with a
    logged LLM prompt) and read from data/processed/controls/disclosed_descriptions.jsonl.
    """
    raise NotImplementedError
