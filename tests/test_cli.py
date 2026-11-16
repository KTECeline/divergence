"""The `divergence` command line: exit codes, inputs and the error paths a user can hit.

The model is faked (as in test_evaluator), so these run without the trained files.
"""

import io
import json
import tarfile

import pytest

from divergence import cli
from divergence.evaluator.trial_runner import TrialError
from tests.test_evaluator import DESC, EXFIL, evaluator
from tests.test_trial_runner import FOLDER, _packed_traces, _skill

QUIET = [{"seq": 0, "step": 0, "source": "tool", "tool": "write", "action": "file_write",
          "target": "tables.md", "status": "ok"}]


@pytest.fixture
def fake_model(monkeypatch):
    """`divergence evaluate` builds DivergenceEvaluator() itself; hand it the fake one."""
    import divergence.evaluator.divergence_evaluator as de
    monkeypatch.setattr(de, "DivergenceEvaluator", lambda: evaluator(intercept=-1.0))


def _write(path, obj):
    path.write_text(json.dumps(obj))
    return str(path)


def test_plugin_name_keeps_only_safe_characters():
    assert cli.plugin_name("my skill@v2") == "my-skill-v2"
    assert cli.plugin_name("computer-use_agents") == "computer-use_agents"


def test_evaluate_allow_prints_the_reasoning_and_exits_0(tmp_path, capsys, fake_model):
    code = cli.main(["evaluate", "--description", DESC, "--trace", _write(tmp_path / "t.json", QUIET)])
    out = capsys.readouterr().out
    assert code == 0 and out.startswith("ALLOW") and "No structural red flag fired." in out


def test_evaluate_flag_exits_1_only_with_fail_on_flag(tmp_path, capsys, fake_model):
    trace = _write(tmp_path / "t.json", EXFIL)
    assert cli.main(["evaluate", "--description", DESC, "--trace", trace]) == 0
    assert capsys.readouterr().out.startswith("FLAG")
    assert cli.main(["evaluate", "--description", DESC, "--trace", trace, "--fail-on-flag"]) == 1
    assert cli.main(["evaluate", "--description", DESC, "--trace", _write(tmp_path / "q.json", QUIET),
                     "--fail-on-flag"]) == 0


def test_evaluate_json_is_the_full_result_object(tmp_path, capsys, fake_model):
    cli.main(["evaluate", "--description", DESC, "--trace", _write(tmp_path / "t.json", EXFIL), "--json"])
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"] == "FLAG" and "flag_unmentioned_domain" in result["structural_flags"]
    assert {"consistency_score", "probability", "reasoning", "flag_evidence", "trace_text"} <= result.keys()


def test_evaluate_reads_the_description_from_skill_md(tmp_path, capsys, fake_model):
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: uploader\ndescription: Uploads notes to the collector-exfil.net service over http.\n---\nbody\n")
    cli.main(["evaluate", "--skill-md", str(md), "--trace", _write(tmp_path / "t.json", EXFIL), "--json"])
    # the same trace that is flagged under DESC is consistent with a description that declares the host
    assert json.loads(capsys.readouterr().out)["structural_flags"] == []


def test_evaluate_agt_log_with_os_events(tmp_path, capsys, fake_model):
    entries = _write(tmp_path / "agt.json", {"entries": [{"action": "bash", "resource": "python3 run.py"}]})
    os_events = _write(tmp_path / "os.json", [{"parent": 0, "action": "dns_lookup", "target": "collector-exfil.net"}])
    assert cli.main(["evaluate", "--description", DESC, "--trace", entries]) == 0
    assert capsys.readouterr().out.startswith("ALLOW")          # AGT's tool-call layer alone shows nothing
    cli.main(["evaluate", "--description", DESC, "--trace", entries, "--os-events", os_events])
    out = capsys.readouterr().out
    assert out.startswith("FLAG") and "collector-exfil.net" in out


def test_evaluate_empty_trace_says_nothing_was_observed(tmp_path, capsys, fake_model):
    """Readable but empty is a result ("nothing observed"), unlike an unreadable trace (exit 2, below)."""
    ran_nothing = {"agent_json": None, "process_events": [], "file_events": [], "network_events": []}
    for name, empty in (("list.json", []), ("agt.json", {"entries": []}), ("raw.json", ran_nothing)):
        assert cli.main(["evaluate", "--description", DESC, "--trace", _write(tmp_path / name, empty)]) == 0
        assert "no observable actions" in capsys.readouterr().out


def test_nothing_observed_is_said_first_and_changes_no_verdict_or_json(tmp_path, capsys, fake_model):
    notice = "NOTICE: nothing was observed during the trial; this is not evidence the skill is safe"
    empty, quiet = _write(tmp_path / "e.json", []), _write(tmp_path / "q.json", QUIET)
    assert cli.main(["evaluate", "--description", DESC, "--trace", empty]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == notice and lines[1] == "" and lines[2].startswith("ALLOW")    # before the verdict

    cli.main(["evaluate", "--description", DESC, "--trace", empty, "--json"])
    out, err = capsys.readouterr()
    result = json.loads(out)                                   # stdout is still exactly the result object
    assert err.strip() == notice and result == evaluator(intercept=-1.0).evaluate(DESC, []).to_dict()
    assert result["verdict"] == "ALLOW"

    cli.main(["evaluate", "--description", DESC, "--trace", quiet])                    # a run that did something
    out, err = capsys.readouterr()
    assert "NOTICE" not in out + err and out.startswith("ALLOW")


def test_missing_model_exits_4_with_a_message(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("DIVERGENCE_MODEL_DIR", str(tmp_path))  # a folder with no model in it
    code = cli.main(["evaluate", "--description", DESC, "--trace", _write(tmp_path / "t.json", QUIET)])
    assert code == 4 and "model not found" in capsys.readouterr().err


# --- invalid input: exit 2, one line on stderr, and never a verdict --------------------------

BAD_TRACES = {
    "not JSON at all": ("{not json", "is not valid JSON (line 1, column 2"),
    "a list of non-objects": ("[1, 2, 3]", "entry 0 is a int"),
    "entries missing required keys": ('[{"action": "file_read"}]', "has neither data.input nor resource"),
    "entries with no tool name": ('[{"foo": 1}]', "entry 0 has no 'action'"),
    "one good action, one broken": ('[{"action": "file_read", "target": "/etc/passwd", "source": "process"}, {"action": "x"}]',
                                    "action 1 is missing source, target"),
    "a normalised action with a non-text target": ('[{"action": "file_read", "target": 5, "source": "process"}]',
                                                   "action 0: 'target' must be text"),
    "a bare string": ('"hello"', "expected a JSON list or object, got str"),
    "an object of no known shape": ("{}", "neither an AGT AuditLog export"),
    "an AuditLog whose entries are not a list": ('{"entries": 5}', "'entries' must be a list"),
    "a sandbox result with the wrong types": ('{"agent_json": "oops", "process_events": 5}', "'agent_json' must be an object"),
    "a sandbox result with broken events": ('{"process_events": [1, 2]}', "'process_events' must be a list of objects"),
}


@pytest.mark.parametrize("case", BAD_TRACES)
def test_unreadable_trace_exits_2_and_is_never_allowed(case, tmp_path, capsys, fake_model):
    content, expected = BAD_TRACES[case]
    trace = tmp_path / "t.json"
    trace.write_text(content)
    for extra in ([], ["--fail-on-flag"], ["--json"]):
        code = cli.main(["evaluate", "--description", DESC, "--trace", str(trace)] + extra)
        out, err = capsys.readouterr()
        assert code == 2, case
        assert out == ""                                           # no verdict of any kind was printed
        assert err.startswith("divergence: invalid input:") and expected in err
        assert err.count("\n") == 1 and "Traceback" not in err    # one line, no stack trace


def test_missing_or_unreadable_files_exit_2(tmp_path, capsys, fake_model):
    good = _write(tmp_path / "t.json", QUIET)
    cases = [(["--description", DESC, "--trace", str(tmp_path / "nope.json")], "trace file not found"),
             (["--description", DESC, "--trace", str(tmp_path)], "cannot read trace file"),          # a folder
             (["--skill-md", str(tmp_path / "SKILL.md"), "--trace", good], "SKILL.md not found"),
             (["--description", DESC, "--trace", good, "--os-events", str(tmp_path / "nope.json")], "OS events file not found")]
    for args, expected in cases:
        assert cli.main(["evaluate"] + args) == 2
        out, err = capsys.readouterr()
        assert out == "" and expected in err and err.count("\n") == 1


def test_no_description_exits_2(tmp_path, capsys, fake_model):
    good = _write(tmp_path / "t.json", QUIET)
    assert cli.main(["evaluate", "--description", "", "--trace", good]) == 2
    assert "--description is empty" in capsys.readouterr().err
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: x\n---\n# title only\n")
    assert cli.main(["evaluate", "--skill-md", str(md), "--trace", good]) == 2
    assert "has no description" in capsys.readouterr().err


def test_bad_os_events_exit_2(tmp_path, capsys, fake_model):
    entries = _write(tmp_path / "agt.json", {"entries": [{"action": "bash", "resource": "python3 run.py"}]})
    orphan = _write(tmp_path / "o.json", [{"parent": 7, "action": "dns_lookup", "target": "collector-exfil.net"}])
    assert cli.main(["evaluate", "--description", DESC, "--trace", entries, "--os-events", orphan]) == 2
    assert "parent 7 is not the index of an audit entry" in capsys.readouterr().err   # it would have been dropped
    not_a_list = _write(tmp_path / "d.json", {"parent": 0})
    assert cli.main(["evaluate", "--description", DESC, "--trace", entries, "--os-events", not_a_list]) == 2
    assert "expected a JSON list" in capsys.readouterr().err


def test_a_crash_is_exit_5_not_the_flag_code(tmp_path, capsys, monkeypatch):
    import divergence.evaluator.divergence_evaluator as de

    def broken():
        raise RuntimeError("boom")

    monkeypatch.setattr(de, "DivergenceEvaluator", broken)
    args = ["evaluate", "--description", DESC, "--trace", _write(tmp_path / "t.json", QUIET), "--fail-on-flag"]
    monkeypatch.delenv("DIVERGENCE_DEBUG", raising=False)
    assert cli.main(args) == 5
    out, err = capsys.readouterr()
    assert out == "" and "no verdict was produced (RuntimeError: boom)" in err and "Traceback" not in err
    monkeypatch.setenv("DIVERGENCE_DEBUG", "1")
    with pytest.raises(RuntimeError, match="boom"):
        cli.main(args)


# --- divergence install (trials captured earlier, so no VM is needed) ----------------------

@pytest.fixture
def captured(tmp_path):
    with tarfile.open(fileobj=io.BytesIO(_packed_traces(FOLDER))) as tar:
        tar.extractall(tmp_path / "traces", filter="data")
    return ["install", "--skill-dir", str(_skill(tmp_path)), "--traces-root", str(tmp_path / "traces"),
            "--out", str(tmp_path / "out")]


def _fake_installer_model(monkeypatch, intercept):
    import divergence.evaluator.agt_installer as inst
    monkeypatch.setattr(inst, "DivergenceEvaluator", lambda: evaluator(intercept=intercept))


def test_install_allow_installs_and_writes_the_report(tmp_path, capsys, monkeypatch, captured):
    _fake_installer_model(monkeypatch, -50.0)
    assert cli.main(captured) == 0
    assert "INSTALLED by AGT" in capsys.readouterr().out
    (run_dir,) = (tmp_path / "out").iterdir()
    report = json.loads((run_dir / "install_report.json").read_text())
    assert report["verdict"] == "ALLOW" and report["suggested_policy_decision"] == "allow"
    assert set(report["runs"]) == {"direct", "instructed"}
    assert json.loads((run_dir / "agt_audit_log.json").read_text())["entry_count"] > 0


def test_install_flag_blocks_with_exit_1_until_approved(tmp_path, capsys, monkeypatch, captured):
    _fake_installer_model(monkeypatch, 50.0)
    assert cli.main(captured) == 1
    assert "BLOCKED" in capsys.readouterr().out
    assert cli.main(captured + ["--approve"]) == 0
    assert "approved -> INSTALLED" in capsys.readouterr().out


def test_install_refused_by_agt_exits_6_with_agts_reason(tmp_path, capsys, monkeypatch, captured):
    from agentmesh.marketplace import MarketplaceError
    from agentmesh.marketplace.installer import PluginInstaller

    reason = "Plugin md-tables@1.0.0 signed by untrusted author 'demo-publisher'"

    def refuse(self, name, version=None, *, verify=True, _seen=None):
        raise MarketplaceError(reason)

    monkeypatch.setattr(PluginInstaller, "install", refuse)     # AGT's own check, after Divergence's
    _fake_installer_model(monkeypatch, -50.0)                   # Divergence itself says ALLOW
    assert cli.main(captured) == 6
    out, err = capsys.readouterr()
    assert err.strip() == f"divergence: blocked by AGT: {reason}"
    assert f">>> BLOCKED by AGT: {reason} (Divergence verdict: ALLOW)" in out and "INSTALLED" not in out
    (run_dir,) = (tmp_path / "out").iterdir()
    report = json.loads((run_dir / "install_report.json").read_text())
    assert report["outcome"].startswith("BLOCKED by AGT") and report["verdict"] == "ALLOW"

    _fake_installer_model(monkeypatch, 50.0)                    # Divergence FLAG, human approves, AGT refuses
    assert cli.main(captured[:-1] + [str(tmp_path / "out2")]) == 1          # exit 1 stays Divergence's FLAG
    capsys.readouterr()
    assert cli.main(captured[:-1] + [str(tmp_path / "out3"), "--approve"]) == 6
    assert "blocked by AGT" in capsys.readouterr().err


def test_install_announces_a_run_with_nothing_observed_before_the_verdict(tmp_path, capsys, monkeypatch):
    _fake_installer_model(monkeypatch, -50.0)
    f = tmp_path / "traces" / "direct_out" / "results" / "candidate" / f"{FOLDER}.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"agent_json": None, "process_events": [], "file_events": [], "network_events": []}))
    code = cli.main(["install", "--skill-dir", str(_skill(tmp_path)), "--traces-root", str(tmp_path / "traces"),
                     "--out", str(tmp_path / "out")])
    out = capsys.readouterr().out
    notice = "NOTICE (direct run): nothing was observed during the trial; this is not evidence the skill is safe"
    assert code == 0 and notice in out and out.index(notice) < out.index("Skill md-tables: ALLOW")


def test_install_sandbox_failure_exits_3(tmp_path, capsys, monkeypatch):
    import divergence.evaluator.trial_runner as tr

    class BrokenRunner:
        def __init__(self, *a, **kw):
            pass

        def run(self, name, skill_dir, audit_log):
            raise TrialError("VM dvg-lab is Stopped")

    monkeypatch.setattr(tr, "LimaTrialRunner", BrokenRunner)   # never touch a real VM from a test
    _fake_installer_model(monkeypatch, 0.0)
    code = cli.main(["install", "--skill-dir", str(_skill(tmp_path)), "--out", str(tmp_path / "out")])
    assert code == 3 and "sandbox trial failed" in capsys.readouterr().err


def test_install_without_a_skill_md_exits_2(tmp_path, capsys):
    assert cli.main(["install", "--skill-dir", str(tmp_path), "--traces-root", str(tmp_path)]) == 2
    assert "no SKILL.md in" in capsys.readouterr().err


def test_install_with_no_captured_trial_exits_3_not_a_traceback(tmp_path, capsys, monkeypatch):
    _fake_installer_model(monkeypatch, -50.0)
    (tmp_path / "empty").mkdir()
    code = cli.main(["install", "--skill-dir", str(_skill(tmp_path)), "--traces-root", str(tmp_path / "empty"),
                     "--out", str(tmp_path / "out")])
    out, err = capsys.readouterr()
    assert code == 3 and "no captured trial run for candidate/md-tables" in err
    assert "INSTALLED" not in out


def test_two_installs_in_the_same_second_get_separate_run_folders(tmp_path, capsys, monkeypatch, captured):
    _fake_installer_model(monkeypatch, -50.0)
    monkeypatch.setattr(cli.time, "strftime", lambda fmt: "20261114-120000")     # freeze the clock
    assert cli.main(captured) == 0 and cli.main(captured) == 0 and cli.main(captured) == 0
    assert sorted(d.name for d in (tmp_path / "out").iterdir()) == [
        "md-tables-20261114-120000", "md-tables-20261114-120000-2", "md-tables-20261114-120000-3"]
    assert all((d / "install_report.json").is_file() for d in (tmp_path / "out").iterdir())
