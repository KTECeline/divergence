"""Enriched trace-to-text conversion (pipeline Step 2, Option 1).

Build order item 5 — the biggest engineering task and an original
contribution. Converts a raw action trace into enriched natural-language
text via rule-based templates. NOT a flat template: sensitive action types
(e.g. sending data to an external, previously unseen domain; credential
access) must be named explicitly in the output text.

Develop and test iteratively in notebooks/02_trace_to_text_dev.ipynb,
with unit tests in tests/test_trace_to_text.py written as you go.
"""


def trace_to_enriched_text(trace: list[dict]) -> str:
    """Convert a raw action trace into enriched descriptive text.

    Example output: "reads a file, then sends data to an external,
    previously unseen domain, then writes a file"
    """
    raise NotImplementedError
