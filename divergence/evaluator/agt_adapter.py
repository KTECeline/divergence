"""Turn an AGT audit log into the action list the Divergence pipeline reads.

AGT 4.1.0 records one `agentmesh.governance.audit.AuditEntry` per tool call
(`action` = tool name, `resource`, `data`, `outcome`). It records nothing below
the tool call: AGT's log shows "ran `python3 run.py`", not what the script then
did (checked from the installed source, sandbox/setup_notes.md). So the adapter
takes two inputs:

  * the AGT entries, one per agent tool call, with the call's raw input in
    `data["input"]` (AGT stores `data` unchanged);
  * the sandbox's OS-level events (strace), each tagged with `parent`, the index
    of the AGT entry whose tool call caused it, or `parent: None` for events no
    tool call caused (direct mode: no agent, so AGT's log is empty).

The tool calls are mapped with the SAME function the dataset was built with
(`normalise_trace.tool_action`), so for one run the adapter's output equals
`normalise(result)`: the trace the model was trained on. `record_trial` /
`check_parity` produce and verify exactly that.

Without the OS events the evaluator still runs, on what AGT alone sees (the
"AGT-visible" condition in notebook 07).

A trace that cannot be read raises TraceFormatError and is never scored. Scoring
it anyway would describe the run as "Unknown", no flag would fire, and the
verdict would come out ALLOW: a pre-install check must not pass a skill because
its evidence was unreadable. An EMPTY trace is different: it is readable and
says nothing was observed, which is reported as such.
"""

from collections.abc import Mapping

from divergence.preprocessing.normalise_trace import call_effects, normalise, tool_action, tool_calls

# AuditEntry.outcome <-> the status values in the captured traces
OUTCOME_STATUS = {"success": "ok", "failure": "failed", "error": "error", "denied": "failed"}
STATUS_OUTCOME = {"ok": "success", "error": "error"}  # anything else ("failed", "?") -> "failure"
DIVERGENCE_KEYS = {"action", "target", "source"}
# for entries without raw input: which tool argument AGT's `resource` holds
RESOURCE_KEY = {"skill": "name", "bash": "command", "read": "filePath", "write": "filePath", "edit": "filePath",
                "webfetch": "url", "task": "description"}
TRIAL_EVENT = "tool_invocation"


class TraceFormatError(ValueError):
    """The trace is not something Divergence can read; nothing was scored."""


def _as_dict(entry, i: int) -> dict:
    """An AuditEntry (pydantic model) or an already-dumped dict."""
    if hasattr(entry, "model_dump"):
        return entry.model_dump()
    if isinstance(entry, Mapping):
        return dict(entry)
    raise TraceFormatError(f"entry {i} is a {type(entry).__name__}, not an action or an AGT audit entry")


def is_divergence_trace(log: list) -> bool:
    """True when the log is already in Divergence's normalised format."""
    return all(isinstance(a, dict) and DIVERGENCE_KEYS <= a.keys() for a in log)


def _check_actions(trace: list[dict]) -> None:
    """A normalised trace: every action names what was done, to what, and at which layer."""
    for i, a in enumerate(trace):
        for key in sorted(DIVERGENCE_KEYS):
            if not isinstance(a[key], str):
                raise TraceFormatError(f"action {i}: '{key}' must be text, got {type(a[key]).__name__}")
        if not a["action"].strip():
            raise TraceFormatError(f"action {i}: 'action' is empty")


def _check_os_events(os_events, n_entries: int) -> None:
    if not isinstance(os_events, (list, tuple)):
        raise TraceFormatError(f"os_events must be a list, got {type(os_events).__name__}")
    for j, ev in enumerate(os_events):
        if not isinstance(ev, Mapping):
            raise TraceFormatError(f"os event {j} is a {type(ev).__name__}, not an object")
        for key in ("action", "target"):
            if not isinstance(ev.get(key), str) or (key == "action" and not ev[key].strip()):
                raise TraceFormatError(f"os event {j} has no '{key}'")
        parent = ev.get("parent")
        if parent is None:
            continue
        try:
            ok = not isinstance(parent, bool) and 0 <= int(parent) < n_entries
        except (TypeError, ValueError):
            ok = False
        if not ok:  # it would be attached to no entry and silently dropped
            raise TraceFormatError(f"os event {j}: parent {parent!r} is not the index of an audit entry "
                                   f"(there are {n_entries})")


def from_agt_audit_log(entries: list, os_events: list[dict] | None = None) -> list[dict]:
    """AGT audit entries (+ the sandbox's OS events) -> Divergence action list.

    os_events: dicts with `parent` (AGT entry index or None), `action`, `target`,
    `status`, and optionally `step` / `tool` (kept for parent-less events, whose
    grouping comes from the sandbox rather than from a tool call).
    """
    if not isinstance(entries, (list, tuple)):
        raise TraceFormatError(f"a trace must be a list of actions or audit entries, got {type(entries).__name__}")
    _check_os_events(os_events or [], len(entries))
    by_parent: dict[int, list[dict]] = {}
    orphans = []
    for ev in os_events or []:
        (orphans if ev.get("parent") is None else by_parent.setdefault(int(ev["parent"]), [])).append(ev)

    actions: list[dict] = []

    def emit(step, source, tool, action, target, status):
        actions.append({"seq": len(actions), "step": step, "source": source, "tool": tool,
                        "action": action, "target": target, "status": status})

    for i, raw in enumerate(entries):
        e = _as_dict(raw, i)
        tool = e.get("action")
        if not isinstance(tool, str) or not tool.strip():
            raise TraceFormatError(f"entry {i} has no 'action' (the tool that was called)")
        data = e.get("data") or {}
        if not isinstance(data, Mapping):
            raise TraceFormatError(f"entry {i} ('{tool}'): 'data' must be an object, got {type(data).__name__}")
        inp = data.get("input") if isinstance(data.get("input"), dict) else None
        if inp is None:
            # an entry from another AGT integration: no raw input, only `resource`
            if not e.get("resource"):
                raise TraceFormatError(f"entry {i} ('{tool}') has neither data.input nor resource: "
                                       "nothing says what the call did")
            key = RESOURCE_KEY.get(tool)
            mapped = tool_action(tool, {key: e.get("resource") or ""}) if key else ("unknown", str(e.get("resource") or ""))
        else:
            mapped = tool_action(tool, inp)
        if mapped is None:
            continue  # planning tool (todowrite etc.), as in normalise()
        status = data.get("status") or OUTCOME_STATUS.get(str(e.get("outcome", "success")), "ok")
        emit(i, "tool", tool, *mapped, status)
        for ev in by_parent.get(i, []):
            emit(i, "process", tool, ev["action"], ev["target"], ev.get("status", "ok"))
    for ev in orphans:
        emit(ev.get("step", 0), "process", ev.get("tool", "script"), ev["action"], ev["target"], ev.get("status", "ok"))
    return actions


def to_divergence_trace(audit_log: list, os_events: list[dict] | None = None) -> list[dict]:
    """Accept either format: a normalised Divergence trace passes through unchanged.

    Raises TraceFormatError for anything else that is not a list of AGT audit
    entries; an unreadable trace is never turned into something scoreable.
    """
    if not isinstance(audit_log, (list, tuple)):
        raise TraceFormatError(f"a trace must be a list of actions or audit entries, got {type(audit_log).__name__}")
    shaped = [isinstance(a, dict) and DIVERGENCE_KEYS <= a.keys() for a in audit_log]
    if any(shaped) and not all(shaped):  # a normalised trace with a broken action: name that one
        i = shaped.index(False)
        if not isinstance(audit_log[i], dict):
            raise TraceFormatError(f"entry {i} is a {type(audit_log[i]).__name__}, not an action")
        raise TraceFormatError(f"action {i} is missing {', '.join(sorted(DIVERGENCE_KEYS - audit_log[i].keys()))}")
    if audit_log and all(shaped):
        if os_events:
            raise TraceFormatError("os_events belong to AGT audit entries; this trace is already normalised "
                                   "and carries its OS-level actions itself")
        _check_actions(audit_log)
        return list(audit_log)
    return from_agt_audit_log(audit_log, os_events)


def agt_visible(trace: list[dict]) -> list[dict]:
    """Only the tool-call layer: what AGT's own audit log would contain."""
    return [a for a in trace if a.get("source") == "tool"]


def record_trial(audit_log, agent_did: str, result: dict, trace_id: str | None = None):
    """Record one sandbox trial run in AGT's AuditLog, as an AGT integration would.

    Each RAW tool call of the run becomes one AuditEntry (tool name, raw input in
    `data`, outcome). OS-level events are attributed to their tool call by the
    sandbox's strace layer and returned separately, since AGT does not record them.
    Returns (entries, os_events) for the evaluator.
    """
    calls = tool_calls(result)
    entries = [audit_log.log(event_type=TRIAL_EVENT, agent_did=agent_did, action=c["tool"],
                             resource=None, data={"input": c["input"], "status": c["status"]},
                             outcome=STATUS_OUTCOME.get(c["status"], "failure"), trace_id=trace_id)
               for c in calls]
    if calls:
        os_events = [{"parent": i, "action": a, "target": t, "status": s}
                     for i, effs in sorted(call_effects(result).items()) for a, t, s in effs]
    else:  # direct mode: no agent; the events come from the sandbox alone
        os_events = [{"parent": None, "step": a["step"], "tool": a["tool"], "action": a["action"],
                      "target": a["target"], "status": a["status"]} for a in normalise(result)]
    return entries, os_events


def check_parity(result: dict, entries: list, os_events: list[dict]) -> tuple[bool, str]:
    """Does the trace rebuilt from AGT's log equal the dataset's normalise() trace?"""
    want, got = normalise(result), from_agt_audit_log(entries, os_events)
    if want == got:
        return True, f"identical ({len(want)} actions)"
    for i, (w, g) in enumerate(zip(want, got)):
        if w != g:
            return False, f"first difference at action {i}: dataset {w} vs AGT {g}"
    return False, f"length differs: dataset {len(want)} vs AGT {len(got)}"
