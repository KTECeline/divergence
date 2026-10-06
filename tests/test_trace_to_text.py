"""Unit tests for enriched trace-to-text conversion (build order item 16).

Write these AS the conversion rules are developed, not at the end — this is
original logic and the most likely source of edge-case bugs.
"""

import pytest

from src.preprocessing.trace_to_text import trace_to_enriched_text


def test_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        trace_to_enriched_text([])
