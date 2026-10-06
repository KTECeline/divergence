"""Structural red-flag rules (pipeline Step 5, Option 2 — no ML).

Build order item 6. Three boolean flags computed from the description +
trace pair, fed alongside cosine similarity into the calibration layer.
Develop against hand-crafted cases in notebooks/03_structural_flags_dev.ipynb,
with unit tests in tests/test_structural_flags.py.
"""

from dataclasses import dataclass


@dataclass
class StructuralFlags:
    flag_unmentioned_domain: bool
    flag_credential_access: bool
    flag_undeclared_action_type: bool

    def as_list(self) -> list[bool]:
        return [
            self.flag_unmentioned_domain,
            self.flag_credential_access,
            self.flag_undeclared_action_type,
        ]

    def raised(self) -> list[str]:
        """Names of the flags that fired, for the evaluator's result object."""
        return [name for name, value in vars(self).items() if value]


def compute_structural_flags(description: str, trace: list[dict]) -> StructuralFlags:
    """Run the three rule-based red-flag checks on a description/trace pair."""
    raise NotImplementedError
