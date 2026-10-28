"""Sentence-BERT load + encode wrapper (pipeline Steps 1 and 3).

Build order item 7 (pretrained-only safety net), later reused with the
SetFit-fine-tuned model from models/finetuned_embedding/.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import PRETRAINED_EMBEDDING_MODEL


class Encoder:
    """Thin wrapper around a sentence-transformers model.

    Loads either the pretrained base model or the fine-tuned model saved in
    models/finetuned_embedding/, and exposes a single encode() method used
    for both descriptions and enriched trace texts.
    """

    def __init__(self, model_name_or_path: str = PRETRAINED_EMBEDDING_MODEL):
        self.name = str(model_name_or_path)
        self.model = SentenceTransformer(self.name)

    @property
    def max_tokens(self) -> int:
        """Longer inputs are truncated by the model, so later text is unseen."""
        return self.model.max_seq_length

    def n_tokens(self, texts: list[str]) -> list[int]:
        return [len(self.model.tokenizer(t)["input_ids"]) for t in texts]

    def encode(self, texts: list[str]) -> np.ndarray:
        """One unit-length vector per text, so a dot product is the cosine."""
        return self.model.encode(texts, batch_size=32, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)
