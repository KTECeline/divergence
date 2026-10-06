"""Sentence-BERT load + encode wrapper (pipeline Steps 1 and 3).

Build order item 7 (pretrained-only safety net), later reused with the
SetFit-fine-tuned model from models/finetuned_embedding/.
"""

from src.config import PRETRAINED_EMBEDDING_MODEL


class Encoder:
    """Thin wrapper around a sentence-transformers model.

    Loads either the pretrained base model or the fine-tuned model saved in
    models/finetuned_embedding/, and exposes a single encode() method used
    for both descriptions and enriched trace texts.
    """

    def __init__(self, model_name_or_path: str = PRETRAINED_EMBEDDING_MODEL):
        raise NotImplementedError

    def encode(self, texts: list[str]):
        raise NotImplementedError
