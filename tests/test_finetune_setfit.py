"""Unit tests for the contrastive fine-tuning pairs (build order item 8).

The label direction is the easy bug here: label 1 means INCONSISTENT, so its
pair must be trained towards cosine 0, never 1.
"""

from src.embedding.finetune_setfit import pair_dataset


def row(label, desc="Get weather forecasts.", trace=None):
    trace = trace or [{"action": "process_exec", "target": "curl https://wttr.in/london", "status": "ok", "step": 1}]
    return {"description": desc, "trace": trace, "label": label}


def test_label_direction():
    ds = pair_dataset([row(0), row(1)])
    assert ds["score"] == [1.0, 0.0]   # consistent -> 1, inconsistent -> 0


def test_pairs_use_description_and_enriched_trace():
    ds = pair_dataset([row(0)])
    assert ds["sentence1"] == ["Get weather forecasts."]
    assert ds["sentence2"] == ["Downloads from wttr.in (london)"]


def test_text_function_is_swappable_for_the_ablation():
    ds = pair_dataset([row(0)], text_fn=lambda trace: "flat")
    assert ds["sentence2"] == ["flat"]
