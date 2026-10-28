"""DivergencePluginInstaller: Divergence runs before AGT's own install checks."""

import warnings

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

warnings.filterwarnings("ignore", category=DeprecationWarning)
from agentmesh.marketplace import MarketplaceError  # noqa: E402
from agentmesh.marketplace.manifest import PluginManifest, PluginType  # noqa: E402
from agentmesh.marketplace.registry import PluginRegistry  # noqa: E402
from agentmesh.marketplace.signing import PluginSigner  # noqa: E402

from src.evaluator.agt_installer import DivergenceEscalation, DivergencePluginInstaller, TrialRun  # noqa: E402
from tests.test_evaluator import DESC, EXFIL, evaluator  # noqa: E402

QUIET = [{"seq": 0, "step": 0, "source": "tool", "tool": "write", "action": "file_write",
          "target": "tables.md", "status": "ok"}]


@pytest.fixture
def installer(tmp_path):
    signer = PluginSigner(ed25519.Ed25519PrivateKey.generate())
    registry = PluginRegistry(tmp_path / "registry.json")
    for name in ("exfil-skill", "quiet-skill"):
        registry.register(signer.sign(PluginManifest(name=name, version="1.0.0", description=DESC,
                                                     author="pub", plugin_type=PluginType.INTEGRATION)))
    return DivergencePluginInstaller(tmp_path / "plugins", registry, {"pub": signer.public_key},
                                     evaluator=evaluator(intercept=-1.0))


def test_flagged_skill_is_escalated_until_approved(installer):
    a = installer.assess("exfil-skill", [TrialRun("direct", EXFIL), TrialRun("agent", QUIET)])
    assert a.verdict == "FLAG" and a.caught_by == ["direct"]          # flag if ANY run flags
    with pytest.raises(DivergenceEscalation):
        installer.install("exfil-skill")
    installer.approve("exfil-skill", reviewer="did:dvg:reviewer")
    assert installer.install("exfil-skill").exists()                  # then AGT's own checks pass


def test_allowed_skill_goes_through_agt_checks(installer):
    assert installer.assess("quiet-skill", [TrialRun("direct", QUIET)]).verdict == "ALLOW"
    assert installer.install("quiet-skill").exists()


def test_unassessed_skill_cannot_install(installer):
    with pytest.raises(MarketplaceError):
        installer.install("quiet-skill")


def test_decisions_are_in_agts_audit_log(installer):
    installer.assess("exfil-skill", [TrialRun("direct", EXFIL)])
    entries = installer.audit_log.export()["entries"]
    assert entries[-1]["policy_decision"] == "escalate" and entries[-1]["resource"] == "exfil-skill"
    assert installer.audit_log.verify_integrity()[0]
