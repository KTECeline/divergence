"""SetFit few-shot contrastive fine-tuning of the embedding model (Step 0).

Build order item 8. Runs once on the fine-tune split (labelled
description/behaviour pairs, consistent + inconsistent), saves the
fine-tuned model to models/finetuned_embedding/, and logs the loss curve.

SetFit's body is trained with a contrastive CosineSimilarityLoss on sentence
pairs. The setfit library builds those pairs from single sentences that share
a label, which does not fit a task whose examples are already PAIRS. So the
same objective is applied directly to each (description, trace text) pair:
consistent (NEG) -> target cosine 1, inconsistent (POS) -> target cosine 0.
The encoder stays a bi-encoder, so the score is still cosine(Vector_A, Vector_B).

Deliberately NOT done: swapped-description augmentation (description of skill A
with trace of skill B). Experiment 5b uses exactly those swaps as a control;
training on them would make the control trivially easy.
"""

import tempfile

import numpy as np
from datasets import Dataset
from sentence_transformers import (
    SentenceTransformer, SentenceTransformerTrainer, SentenceTransformerTrainingArguments, losses,
)
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from src.config import FINETUNED_EMBEDDING_DIR, PRETRAINED_EMBEDDING_MODEL, RANDOM_SEED
from src.embedding.similarity import consistency_scores
from src.preprocessing.trace_to_text import trace_to_enriched_text

LEARNING_RATE = 2e-5  # SetFit's default body learning rate
BATCH_SIZE = 16


def pair_dataset(rows: list[dict], text_fn=trace_to_enriched_text) -> Dataset:
    return Dataset.from_dict({
        "sentence1": [r["description"] for r in rows],
        "sentence2": [text_fn(r["trace"]) for r in rows],
        "score": [1.0 - r["label"] for r in rows],   # label 1 = inconsistent -> cosine target 0
    })


def finetune(rows: list[dict], text_fn=trace_to_enriched_text, epochs: int = 3, seed: int = RANDOM_SEED,
             base: str = PRETRAINED_EMBEDDING_MODEL) -> tuple[SentenceTransformer, list[dict]]:
    """Fine-tune a fresh copy of the base encoder; returns it and the logged loss per step."""
    model = SentenceTransformer(base, device="cpu")       # CPU: reproducible, and fast enough
    args = SentenceTransformerTrainingArguments(
        output_dir=tempfile.mkdtemp(prefix="dvg-setfit-"), num_train_epochs=epochs,
        per_device_train_batch_size=BATCH_SIZE, learning_rate=LEARNING_RATE, warmup_ratio=0.1,
        seed=seed, data_seed=seed, logging_steps=1, save_strategy="no", report_to="none",
        use_cpu=True, disable_tqdm=True)
    trainer = SentenceTransformerTrainer(model=model, args=args, train_dataset=pair_dataset(rows, text_fn),
                                         loss=losses.CosineSimilarityLoss(model))
    trainer.train()
    history = [{"step": h["step"], "epoch": h["epoch"], "loss": h["loss"]}
               for h in trainer.state.log_history if "loss" in h]
    return model, history


def score(model: SentenceTransformer, rows: list[dict], text_fn=trace_to_enriched_text) -> np.ndarray:
    """Consistency score in [0, 1] for each row (high = consistent)."""
    enc = lambda texts: model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    return consistency_scores(enc([r["description"] for r in rows]), enc([text_fn(r["trace"]) for r in rows]))


def cv_auc(rows: list[dict], text_fn=trace_to_enriched_text, epochs: int = 3, n_folds: int = 5,
           seed: int = RANDOM_SEED) -> float:
    """Mean held-out-fold AUC inside the given rows, folds grouped by skill so variants stay together."""
    y = np.array([r["label"] for r in rows])
    groups = [r["group_key"] or r["sample_id"] for r in rows]
    folds = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    aucs = []
    for tr, va in folds.split(np.zeros(len(rows)), y, groups):
        model, _ = finetune([rows[i] for i in tr], text_fn, epochs, seed)
        s = score(model, [rows[i] for i in va], text_fn)
        aucs.append(roc_auc_score(y[va], -s))   # minus: LOW score should mean POS
    return float(np.mean(aucs))


def save(model: SentenceTransformer, path=FINETUNED_EMBEDDING_DIR) -> None:
    path.mkdir(parents=True, exist_ok=True)
    model.save(str(path))
