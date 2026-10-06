"""Unit tests for structural red-flag rules (build order item 16).

Cover hand-crafted cases for each of the three flags as the rules are
developed.
"""

import pytest

from src.preprocessing.structural_flags import StructuralFlags, compute_structural_flags


def test_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        compute_structural_flags("", [])


def test_flags_raised_names():
    flags = StructuralFlags(
        flag_unmentioned_domain=True,
        flag_credential_access=False,
        flag_undeclared_action_type=True,
    )
    assert flags.raised() == ["flag_unmentioned_domain", "flag_undeclared_action_type"]
    assert flags.as_list() == [True, False, True]
