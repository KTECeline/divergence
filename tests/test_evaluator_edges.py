"""Evaluator, AGT adapter, installer, trial-runner and model-store behaviour the main test files
do not reach: the probability arithmetic, the 0.5 boundary, and the failure branches."""

import json
import math
import subprocess

import numpy as np
import pytest
from agentmesh.governance.audit import AuditLog
from agentmesh.marketplace import MarketplaceError

import divergence.evaluator.divergence_evaluator as de
import divergence.evaluator.trial_runner as tr
from divergence import model_store
from divergence.calibration.logistic_calibrator import LogisticCalibrator
from divergence.config import CALIBRATION_MODEL_PATH
from divergence.evaluator.agt_adapter import (TraceFormatError, check_parity, from_agt_audit_log, record_trial,
                                              to_divergence_trace)
from divergence.evaluator.divergence_evaluator import DivergenceEvaluator
from divergence.evaluator.trial_runner import CapturedTraceRunner, LimaTrialRunner, TrialError, load_trial_runs
from divergence.model_store import ModelNotFound, resolve_model
from divergence.preprocessing.normalise_trace import normalise
from tests.test_evaluator import DESC, EXFIL, calibrator, evaluator
from tests.test_normalise_trace import _execve, _result
from tests.test_trial_runner import FOLDER, FakeLima, _installer, _skill

QUIET = [{"seq": 0, "step": 0, "source": "tool", "tool": "write", "action": "file_write",
          "target": "tables.md", "status": "ok"}]


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


class OrthogonalEncoder:
    """Descriptions and trace texts get perpendicular vectors -> cosine 0 -> consistency score 0.5."""
    def encode(self, texts):
        return np.array([[1.0, 0.0] if t == DESC else [0.0, 1.0] for t in texts])


# --- evaluator ---------------------------------------------------------------------------

def test_probability_is_the_logistic_of_the_weighted_inputs():
    """Hand calculation: intercept + w_score * score + the weight of each flag that fired."""
    r = DivergenceEvaluator(encoder=OrthogonalEncoder(), calibrator=calibrator(intercept=0.2)).evaluate(DESC, EXFIL)
    assert r.consistency_score == 0.5
    assert r.structural_flags == ["flag_unmentioned_domain", "flag_undeclared_action_type"]
    #            intercept  score      domain  undeclared action type
    assert r.probability == round(sigmoid(0.2 - 1.0 * 0.5 + 3.0 + 0.5), 4)


def test_a_probability_of_exactly_one_half_is_a_flag():
    r = evaluator(intercept=1.0).evaluate(DESC, QUIET)     # score 1.0, no flag: 1.0 - 1.0 = 0 -> p = 0.5
    assert r.probability == 0.5 and r.verdict == "FLAG"
    assert evaluator(intercept=0.99).evaluate(DESC, QUIET).verdict == "ALLOW"


def test_reasoning_names_every_flag_with_its_evidence_and_weight():
    trace = [{"source": "process", "action": "file_read", "target": "/root/.aws/credentials", "status": "ok"},
             {"source": "process", "action": "file_write", "target": "/root/.bashrc", "status": "ok"}]
    r = evaluator().evaluate(DESC, trace)
    assert r.structural_flags == ["flag_credential_access", "flag_undeclared_action_type"]
    assert "/root/.aws/credentials (weight +0.50)" in r.reasoning
    assert "persistence (weight +0.50)" in r.reasoning
    assert r.flag_evidence["unmentioned_hosts"] == []


def test_default_constructor_loads_the_resolved_encoder_and_calibration(tmp_path, monkeypatch):
    calibrator(intercept=0.25).save(tmp_path / "calibration_model.json")
    loaded = []

    class StubEncoder:
        def __init__(self, path):
            loaded.append(path)

    monkeypatch.setattr(de, "resolve_model", lambda: (tmp_path / "enc", tmp_path / "calibration_model.json"))
    monkeypatch.setattr(de, "Encoder", StubEncoder)
    ev = DivergenceEvaluator()
    assert loaded == [str(tmp_path / "enc")]
    assert ev.weights["intercept"] == 0.25 and ev.weights["flag_unmentioned_domain"] == 3.0


@pytest.mark.skipif(not CALIBRATION_MODEL_PATH.is_file(), reason="trained model not in this checkout")
def test_shipped_calibration_matches_a_hand_calculation():
    """The saved JSON is plain weights: its output must equal the logistic formula worked by hand."""
    d = json.loads(CALIBRATION_MODEL_PATH.read_text())
    assert d["threshold"] == 0.5 and len(d["coef"]) == len(d["feature_names"]) == 4
    x = [0.5766, 1.0, 0.0, 1.0]        # score, unmentioned domain, credential access, undeclared action type
    by_hand = sigmoid(d["intercept"] + sum(w * v for w, v in zip(d["coef"], x)))
    assert LogisticCalibrator.load(CALIBRATION_MODEL_PATH).predict_proba([x])[0] == pytest.approx(by_hand, abs=1e-12)


@pytest.mark.parametrize("trace, message", [
    ([{"action": "file_read"}], "neither data.input nor resource"),      # was scored as "Unknown" -> ALLOW
    ([{"foo": 1}], "has no 'action'"),
    ([1, 2, 3], "entry 0 is a int"),
    ({"action": "bash"}, "must be a list"),
    ("curl evil.example", "must be a list"),
    ([{"action": "", "target": "x", "source": "tool"}], "'action' is empty"),
    ([{"action": "bash", "data": "raw text"}], "'data' must be an object"),
])
def test_python_api_refuses_an_unreadable_trace_instead_of_scoring_it(trace, message):
    with pytest.raises(TraceFormatError, match=message):
        evaluator(intercept=-50.0).evaluate(DESC, trace)        # this calibrator would ALLOW anything


def test_unreadable_trace_fails_the_whole_batch():
    with pytest.raises(TraceFormatError):
        evaluator().evaluate_batch([(DESC, QUIET), (DESC, [{"action": "file_read"}])])


# --- AGT adapter -------------------------------------------------------------------------

def test_os_events_must_point_at_a_real_entry_and_only_at_agt_entries():
    entries = [{"action": "bash", "resource": "python3 run.py"}]
    event = {"action": "dns_lookup", "target": "evil.example"}
    assert len(to_divergence_trace(entries, [{**event, "parent": 0}])) == 2
    for parent in (1, -1, "x", True):
        with pytest.raises(TraceFormatError, match="not the index of an audit entry"):
            to_divergence_trace(entries, [{**event, "parent": parent}])
    with pytest.raises(TraceFormatError, match="os event 0 has no 'target'"):
        to_divergence_trace(entries, [{"parent": 0, "action": "dns_lookup"}])
    with pytest.raises(TraceFormatError, match="already normalised"):
        to_divergence_trace(QUIET, [{**event, "parent": 0}])
    assert to_divergence_trace([], [{**event, "parent": None}])[0]["target"] == "evil.example"   # direct mode



def test_direct_mode_trial_has_no_agt_entries_only_os_events():
    result = {"process_events": [_execve(31, ["/usr/bin/python3", "scripts/run.py"])],
              "file_events": [{"pid": "31", "syscall": "openat", "path": "/root/.ssh/id_rsa",
                               "args": '"/root/.ssh/id_rsa", O_RDONLY', "return": 3}],
              "network_events": []}
    entries, os_events = record_trial(AuditLog(), "did:dvg:test", result)
    assert entries == [] and os_events and all(e["parent"] is None for e in os_events)
    assert from_agt_audit_log(entries, os_events) == normalise(result)
    assert check_parity(result, entries, os_events)[0]


def test_parity_check_reports_what_differs():
    result = _result()
    entries, os_events = record_trial(AuditLog(), "did:dvg:test", result)
    tampered = [{**os_events[0], "target": "something-else"}] + os_events[1:]
    ok, msg = check_parity(result, entries, tampered)
    assert not ok and msg.startswith("first difference at action")
    extra = os_events + [{"parent": None, "action": "dns_lookup", "target": "late.example"}]
    ok, msg = check_parity(result, entries, extra)
    assert not ok and msg.startswith("length differs")


# --- installer and trial runner ----------------------------------------------------------

def test_assess_refuses_a_skill_with_no_trial_runs(tmp_path):
    with pytest.raises(MarketplaceError, match="No trial runs"):
        _installer(tmp_path, None, 0.0).assess("md-tables", [])


def test_a_trace_that_fails_parity_is_not_scored(tmp_path, monkeypatch):
    f = tmp_path / "direct_out" / "results" / "candidate" / f"{FOLDER}.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps(_result()))
    monkeypatch.setattr(tr, "check_parity", lambda *a: (False, "first difference at action 0"))
    with pytest.raises(TrialError, match="parity failed"):
        load_trial_runs(tmp_path, "candidate", FOLDER, ["direct"], AuditLog())


def test_a_trial_with_no_run_or_an_unreadable_result_is_a_trial_error(tmp_path):
    with pytest.raises(TrialError, match="no captured trial run"):
        CapturedTraceRunner(tmp_path, "candidate").run("md-tables", tmp_path / FOLDER, AuditLog())
    f = tmp_path / "direct_out" / "results" / "candidate" / f"{FOLDER}.json"
    f.parent.mkdir(parents=True)
    f.write_text("{cut off")
    with pytest.raises(TrialError, match="not readable JSON"):
        CapturedTraceRunner(tmp_path, "candidate").run("md-tables", tmp_path / FOLDER, AuditLog())


def test_lima_timeout_and_missing_limactl_are_trial_errors(tmp_path):
    def times_out(args, **kw):
        raise subprocess.TimeoutExpired(args, 1)

    def not_installed(args, **kw):
        raise FileNotFoundError("limactl")

    with pytest.raises(TrialError, match="timed out"):
        LimaTrialRunner(local_root=tmp_path, run=times_out).run("md-tables", _skill(tmp_path), AuditLog())
    with pytest.raises(TrialError, match="not found"):
        LimaTrialRunner(local_root=tmp_path, run=not_installed).run("md-tables", _skill(tmp_path), AuditLog())


def test_missing_trial_script_is_reported_before_the_vm_is_touched(tmp_path):
    fake = FakeLima()
    runner = LimaTrialRunner(local_root=tmp_path, run=fake, trial_script=tmp_path / "nope.sh")
    with pytest.raises(TrialError, match="trial script not found"):
        runner.run("md-tables", _skill(tmp_path), AuditLog())
    assert fake.calls == []


# --- model store -------------------------------------------------------------------------

def test_hub_snapshot_without_the_calibration_file_is_an_error(tmp_path, monkeypatch):
    import huggingface_hub
    monkeypatch.delenv("DIVERGENCE_MODEL_DIR", raising=False)
    monkeypatch.setattr(model_store, "FINETUNED_EMBEDDING_DIR", tmp_path / "none")
    (tmp_path / "hub").mkdir()
    (tmp_path / "hub" / "config.json").write_text("{}")          # encoder there, calibration_model.json not
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda repo, revision: str(tmp_path / "hub"))
    with pytest.raises(ModelNotFound, match="missing"):
        resolve_model()
