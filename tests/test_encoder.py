"""The encoder wrapper and the scoring / saving helpers of the fine-tuning module.

SentenceTransformer is stubbed: these check how the wrapper CALLS the model, not the
model. Training itself (finetune, cv_auc) is not unit-tested; it is exercised by
notebook 05 and the experiments, and takes minutes.
"""

import numpy as np

import divergence.embedding.encoder as encoder_module
from divergence.config import PRETRAINED_EMBEDDING_MODEL
from divergence.embedding.encoder import Encoder
from divergence.embedding.finetune_setfit import save, score


class StubModel:
    max_seq_length = 256

    def __init__(self, name="stub"):
        self.name, self.kwargs, self.saved = name, None, None

    def tokenizer(self, text):
        return {"input_ids": text.split()}

    def encode(self, texts, **kwargs):
        self.kwargs = kwargs
        # one direction per distinct first word, so equal first words -> cosine 1
        return np.array([[1.0, 0.0] if t.split()[0] == "formats" else [0.0, 1.0] for t in texts])

    def save(self, path):
        self.saved = path


def test_encoder_defaults_to_the_pretrained_base_and_normalises(monkeypatch):
    monkeypatch.setattr(encoder_module, "SentenceTransformer", StubModel)
    enc = Encoder()
    assert enc.name == enc.model.name == PRETRAINED_EMBEDDING_MODEL
    assert enc.encode(["formats tables", "sends data"]).shape == (2, 2)
    assert enc.model.kwargs["normalize_embeddings"] is True     # a dot product is then the cosine
    assert enc.max_tokens == 256 and enc.n_tokens(["a b c", "d"]) == [3, 1]


def test_encoder_loads_a_given_path(monkeypatch):
    monkeypatch.setattr(encoder_module, "SentenceTransformer", StubModel)
    assert Encoder("models/finetuned_embedding").model.name == "models/finetuned_embedding"


def test_score_is_high_when_description_and_trace_text_agree():
    rows = [{"description": "formats tables", "trace": "same"}, {"description": "formats tables", "trace": "other"}]
    text_fn = lambda trace: "formats a file" if trace == "same" else "sends data out"
    s = score(StubModel(), rows, text_fn)
    assert s.tolist() == [1.0, 0.5]                              # cosine 1 -> 1.0, cosine 0 -> 0.5


def test_save_creates_the_folder_and_saves_there(tmp_path):
    model = StubModel()
    save(model, tmp_path / "models" / "finetuned_embedding")
    assert (tmp_path / "models" / "finetuned_embedding").is_dir()
    assert model.saved == str(tmp_path / "models" / "finetuned_embedding")
