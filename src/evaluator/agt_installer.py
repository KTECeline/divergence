"""DivergencePluginInstaller: AGT's marketplace installer with a Divergence
pre-install check.

AGT 4.1.0 has no registration hook for third-party evaluators (checked from the
installed source). `PromptDefenseEvaluator` is called by user code, and
`agentmesh.marketplace.installer.PluginInstaller.install()` runs a fixed list of
checks: Ed25519 signature -> dependencies -> manifest write -> static scan of
Python imports. So Divergence extends that installer: it subclasses
`PluginInstaller`, and `install()` first requires a Divergence assessment of the
skill's sandbox trial runs, then hands over to AGT's own checks unchanged.
AGT's import scan reads the code; Divergence adds a dynamic, behavioural check
against the manifest's declared description.

Flow:
    installer.assess(name, trial_runs)   # trial runs from the sealed sandbox
    installer.install(name)              # FLAG -> DivergenceEscalation unless approved
    installer.approve(name, reviewer)    # a human reviewer accepts the flagged skill

Each assessment and approval is written to AGT's Merkle-chained AuditLog with
an AGT 4.1.0 PolicyDecision value ("escalate" / "allow") as `policy_decision`.

A skill is FLAGged if ANY of its trial runs (direct / instructed / agent) is
flagged; each run is scored on its own because the model was trained on single
runs. This rule was fixed before any skill-level result was computed.
"""

from dataclasses import dataclass, field
from pathlib import Path

from agentmesh.governance.audit import AuditLog
from agentmesh.marketplace import MarketplaceError
from agentmesh.marketplace.installer import PluginInstaller

from src.config import VERDICT_ALLOW, VERDICT_FLAG
from src.evaluator.divergence_evaluator import AGT_DECISION, DivergenceEvaluator, DivergenceResult

ASSESSMENT_EVENT = "divergence_assessment"
APPROVAL_EVENT = "divergence_approval"
INSTALLER_DID = "did:dvg:installer"


class DivergenceEscalation(MarketplaceError):
    """Install stopped: the skill's behaviour diverged from its description and needs a human."""

    def __init__(self, assessment: "SkillAssessment"):
        self.assessment = assessment
        super().__init__(f"Divergence flagged {assessment.name} (caught in: {', '.join(assessment.caught_by)}); "
                         f"approve() after review to install.\n{assessment.summary()}")


@dataclass
class TrialRun:
    """One sandbox trial run: its AGT audit entries and the sandbox's OS events."""
    mode: str  # "direct" / "instructed" / "agent"
    audit_entries: list
    os_events: list[dict] = field(default_factory=list)


@dataclass
class SkillAssessment:
    name: str
    description: str
    runs: dict[str, DivergenceResult]  # mode -> result

    @property
    def caught_by(self) -> list[str]:
        return [m for m, r in self.runs.items() if r.verdict == VERDICT_FLAG]

    @property
    def verdict(self) -> str:
        return VERDICT_FLAG if self.caught_by else VERDICT_ALLOW

    def to_agt_evidence(self) -> dict:
        return {"evaluator": "divergence", "skill": self.name, "verdict": self.verdict,
                "suggested_policy_decision": AGT_DECISION[self.verdict], "caught_by": self.caught_by,
                "runs": {m: {"probability": r.probability, "consistency_score": r.consistency_score,
                             "structural_flags": r.structural_flags, "verdict": r.verdict}
                         for m, r in self.runs.items()}}

    def summary(self) -> str:
        lines = [f"Skill {self.name}: {self.verdict} (suggested AGT decision: {AGT_DECISION[self.verdict]})"]
        for m, r in self.runs.items():
            lines.append(f"\n--- {m} run ---\n{r.reasoning}")
        return "\n".join(lines)


class DivergencePluginInstaller(PluginInstaller):
    def __init__(self, plugins_dir: Path, registry, trusted_keys=None, *,
                 evaluator: DivergenceEvaluator | None = None, audit_log: AuditLog | None = None):
        super().__init__(plugins_dir, registry, trusted_keys)
        self.evaluator = evaluator or DivergenceEvaluator()
        self.audit_log = audit_log or AuditLog()
        self._assessments: dict[str, SkillAssessment] = {}
        self._approved: set[str] = set()

    def assess(self, name: str, trial_runs: list[TrialRun], version: str | None = None) -> SkillAssessment:
        """Score the skill's trial runs against the description in its registry manifest."""
        if not trial_runs:
            raise MarketplaceError(f"No trial runs for {name}: Divergence needs observed behaviour")
        description = self._registry.get_plugin(name, version).description
        results = self.evaluator.evaluate_batch([(description, t.audit_entries, t.os_events) for t in trial_runs])
        a = SkillAssessment(name, description, {t.mode: r for t, r in zip(trial_runs, results)})
        self._assessments[name] = a
        self.audit_log.log(event_type=ASSESSMENT_EVENT, agent_did=INSTALLER_DID, action="pre_install_check",
                           resource=name, data=a.to_agt_evidence(),
                           outcome="denied" if a.verdict == VERDICT_FLAG else "success",
                           policy_decision=AGT_DECISION[a.verdict])
        return a

    def approve(self, name: str, reviewer: str) -> None:
        """A human reviewer accepts a flagged skill after reading the evidence."""
        self._approved.add(name)
        self.audit_log.log(event_type=APPROVAL_EVENT, agent_did=INSTALLER_DID, action="human_approval",
                           resource=name, data={"reviewer": reviewer}, outcome="success",
                           policy_decision="allow", approver_did=reviewer)

    def install(self, name: str, version: str | None = None, *, verify: bool = True, _seen=None) -> Path:
        """Divergence first, then AGT's own install checks (signature, dependencies, import scan)."""
        a = self._assessments.get(name)
        if a is None:
            raise MarketplaceError(f"{name} has not been assessed by Divergence; call assess() with its trial runs")
        if a.verdict == VERDICT_FLAG and name not in self._approved:
            raise DivergenceEscalation(a)
        return super().install(name, version, verify=verify, _seen=_seen)
