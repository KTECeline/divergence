"""Plugin packaging: where the model comes from, and which trace files the CLI reads."""

import json

import pytest

from divergence import model_store
from divergence.cli import build_parser, load_trace
from divergence.model_store import ModelNotFound, resolve_model
from tests.test_normalise_trace import _result


def _bundle(d):
    d.mkdir(parents=True)
    (d / "config.json").write_text("{}")
    (d / "calibration_model.json").write_text("{}")
    return d


def test_env_model_dir_wins(tmp_path, monkeypatch):
    b = _bundle(tmp_path / "b")
    monkeypatch.setenv("DIVERGENCE_MODEL_DIR", str(b))
    assert resolve_model() == (b, b / "calibration_model.json")


def test_incomplete_env_model_dir_is_a_clear_error(tmp_path, monkeypatch):
    (tmp_path / "b").mkdir()
    monkeypatch.setenv("DIVERGENCE_MODEL_DIR", str(tmp_path / "b"))
    with pytest.raises(ModelNotFound, match="calibration_model.json"):
        resolve_model()


def test_repo_models_then_hub(tmp_path, monkeypatch):
    monkeypatch.delenv("DIVERGENCE_MODEL_DIR", raising=False)
    enc = _bundle(tmp_path / "models" / "finetuned_embedding")
    monkeypatch.setattr(model_store, "FINETUNED_EMBEDDING_DIR", enc)
    monkeypatch.setattr(model_store, "CALIBRATION_MODEL_PATH", enc / "calibration_model.json")
    assert resolve_model()[0] == enc                       # development checkout: models/

    monkeypatch.setattr(model_store, "FINETUNED_EMBEDDING_DIR", tmp_path / "none")
    hub = _bundle(tmp_path / "hub")
    import huggingface_hub
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda repo, revision: str(hub))
    assert resolve_model() == (hub, hub / "calibration_model.json")   # pip install: the Hub

    def offline(repo, revision):
        raise OSError("offline")
    monkeypatch.setattr(huggingface_hub, "snapshot_download", offline)
    with pytest.raises(ModelNotFound, match="DIVERGENCE_MODEL_DIR"):
        resolve_model()


def test_load_trace_accepts_every_format(tmp_path):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(_result()))
    trace = load_trace(raw)                                 # raw sandbox result -> normalised
    assert trace and {"action", "target", "source"} <= trace[0].keys()

    exported = tmp_path / "agt.json"
    exported.write_text(json.dumps({"entry_count": 1, "entries": [{"action": "bash"}]}))
    assert load_trace(exported) == [{"action": "bash"}]     # AuditLog.export()

    lst = tmp_path / "list.json"
    lst.write_text(json.dumps(trace))
    assert load_trace(lst) == trace                         # already normalised


def test_cli_parses_both_commands():
    p = build_parser()
    assert p.parse_args(["evaluate", "--description", "x", "--trace", "t.json"]).command == "evaluate"
    a = p.parse_args(["install", "--skill-dir", "s", "--traces-root", "c"])
    assert a.command == "install" and a.vm == "dvg-lab"
