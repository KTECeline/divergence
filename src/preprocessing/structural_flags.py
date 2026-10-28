"""Structural red-flag rules (pipeline Step 5, Option 2 — no ML).

Build order item 6. Three boolean flags computed from the description +
trace pair, fed alongside cosine similarity into the calibration layer.
Develop against hand-crafted cases in notebooks/04_structural_flags.ipynb,
with unit tests in tests/test_structural_flags.py.

Every flag asks the same question as the whole system, in rule form: did the
trace do something of a kind the description does not declare? So each one
compares the two sides; none fires on behaviour alone. A credential manager
reading credentials is consistent, and a weather skill doing so is not.

Trace parsing (hosts, tool-internal reads, sinkhole) is shared with
trace_to_text.py, so the flags and the enriched text agree on what happened.
Known limitation: the description vocabulary is English, so a non-English
description declares nothing and flags fire more easily on it.
"""

import ipaddress
import re
from dataclasses import dataclass, field

from src.data.outcome import PACKAGE_DOMAINS, PERSISTENCE_RE, SENSITIVE_RE
from src.preprocessing.trace_to_text import (
    DEV_TCP, IP, MINERS, NETRC_READERS, REVERSE_SHELL, SINKHOLE_IP, TOOL_CONFIG_READS, URL, _host, _program,
)

# labels that say nothing about WHICH service a host is ("api.github.com" -> "github")
HOST_NOISE = {"www", "api", "cdn", "app", "apps", "static", "raw", "dl", "download", "files", "data",
              "com", "org", "net", "io", "ai", "co", "uk", "ac", "dev", "xyz", "me", "sh", "cloud",
              "info", "biz", "us", "eu", "de", "cn", "ru", "top", "site", "online", "gov", "edu", "up"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
# Software-distribution infrastructure, treated like the package registries: fetching
# from it is generic. Trade-off (stated in the report): a payload hosted on GitHub
# does not trip flag_unmentioned_domain, though the enriched text still names it.
INFRA_HOSTS = {"github.com", "api.github.com", "raw.githubusercontent.com", "objects.githubusercontent.com",
               "codeload.github.com", "registry.npmjs.com", "astral.sh", "opencode.ai"}
HOSTNAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")

# description vocabulary that declares each action type (matched as word stems)
DECLARES = {
    "network": r"api|http|url|web|online|internet|fetch|download|upload|sync|cloud|server|endpoint|request|"
               r"search|brows|website|remote|network|webhook|email|e-mail|slack|telegram|discord|"
               r"post|publish|deploy|send|notif|integrat|connect|service|platform|stream|feed|scrap|crawl|"
               r"market|price|trad|wallet|blockchain|chain|token|weather|news|install|registry|github|repo",
    "persistence": r"startup|boot|cron|schedul|daemon|background|autostart|bashrc|profile|shell config|"
                   r"hook|login|systemd|recurring|periodic|monitor|watch",
    "deletion": r"delet|remov|clean|purg|wip|uninstall|prun|clear|reset",
    "privilege": r"sudo|root|admin|privileg|permission|user account|ownership|chown",
    "encoded_payload": r"base64|encod|decod|obfuscat|minif|crypto.?min|mining|miner",
    "remote_shell": r"reverse shell|remote shell|ssh|terminal|tunnel",
}
CREDENTIAL_WORDS = (r"credential|secret|password|passwd|api.?key|token|auth|login|ssh|aws|gcp|gcloud|azure|"
                    r"kube|docker|keychain|wallet|private key|\bkeys?\b|vault|certificate|\.env|netrc|cookie")
MASS_DELETE = 10  # deletes at or above this count are a "deletion" action


def _mentions(description: str, pattern: str) -> bool:
    return re.search(rf"\b({pattern})", description.lower()) is not None


def _service_names(host: str) -> list[str]:
    return [l for l in re.split(r"[.\-]", host) if len(l) >= 3 and l not in HOST_NOISE and not l.isdigit()]


def _host_mentioned(host: str, description: str) -> bool:
    d = description.lower()
    if host in d:
        return True
    squashed = re.sub(r"[\s\-_.]", "", d)
    return any(n in d or n in squashed for n in _service_names(host))


def _external(host: str) -> bool:
    """A real, public, non-infrastructure host (rejects command lines cut mid-URL)."""
    if IP.match(host):
        return ipaddress.ip_address(host).is_global and host != SINKHOLE_IP
    return bool(HOSTNAME.match(host)) and host not in LOCAL_HOSTS | PACKAGE_DOMAINS | INFRA_HOSTS


def _observed(trace: list[dict]) -> dict:
    """What the trace did, in the categories the flags compare against."""
    hosts, cred_reads, kinds = [], [], set()
    deletes, last_prog = 0, ""
    for a in trace:
        act, tgt = a["action"], a.get("target", "")
        if act in ("process_exec", "command"):
            prog, args = _program(tgt)
            if act == "process_exec":
                last_prog = prog
            if REVERSE_SHELL.search(tgt) or prog in ("nc", "ncat", "netcat", "socat"):
                kinds.add("remote_shell")
            if MINERS.search(tgt) or (prog == "base64" and re.search(r"(^|\s)(-d|-D|--decode)\b", " ".join(args))):
                kinds.add("encoded_payload")
            if prog in ("crontab", "systemctl", "service"):
                kinds.add("persistence")
            if prog in ("sudo", "su", "useradd", "usermod", "passwd", "chpasswd", "chown", "visudo"):
                kinds.add("privilege")
            for u in URL.findall(tgt):
                hosts.append(_host(u))
            if m := DEV_TCP.search(tgt):
                hosts.append(m.group(2).lower())
        elif act == "file_read":
            if TOOL_CONFIG_READS.search(tgt) or (tgt.endswith("/.netrc") and last_prog in NETRC_READERS):
                continue
            if SENSITIVE_RE.search(tgt):
                cred_reads.append(tgt)
        elif act == "file_write" and PERSISTENCE_RE.search(tgt):
            kinds.add("persistence")
        elif act == "file_delete" and not tgt.startswith("/tmp/"):
            deletes += 1
        elif act in ("dns_lookup", "web_fetch"):
            hosts.append(_host(tgt))
        elif act == "network_connect":
            ip = tgt.rpartition(":")[0]
            if IP.match(ip):
                hosts.append(ip)
    hosts = [h for h in dict.fromkeys(hosts) if _external(h)]
    if hosts:
        kinds.add("network")
    if deletes >= MASS_DELETE:
        kinds.add("deletion")
    return {"hosts": hosts, "credential_reads": cred_reads, "kinds": kinds}


@dataclass
class StructuralFlags:
    flag_unmentioned_domain: bool
    flag_credential_access: bool
    flag_undeclared_action_type: bool
    # why each flag fired, for the evaluator's reasoning text; not a feature
    evidence: dict = field(default_factory=dict, compare=False, repr=False)

    NAMES = ("flag_unmentioned_domain", "flag_credential_access", "flag_undeclared_action_type")

    def as_list(self) -> list[bool]:
        return [getattr(self, n) for n in self.NAMES]

    def raised(self) -> list[str]:
        """Names of the flags that fired, for the evaluator's result object."""
        return [n for n in self.NAMES if getattr(self, n)]


def compute_structural_flags(description: str, trace: list[dict]) -> StructuralFlags:
    """Run the three rule-based red-flag checks on a description/trace pair.

    * flag_unmentioned_domain: the trace contacts an external host (package
      registries and localhost aside) whose service name the description
      never mentions. A raw IP address is never "mentioned".
    * flag_credential_access: the skill reads a credential file (tool-internal
      reads excluded) and the description says nothing about credentials.
    * flag_undeclared_action_type: the trace performs an action TYPE (network,
      persistence, mass deletion, privilege change, encoded payload, remote
      shell) for which the description has no vocabulary at all.
    """
    seen = _observed(trace)
    unmentioned = [h for h in seen["hosts"] if not _host_mentioned(h, description)]
    creds = seen["credential_reads"] if not _mentions(description, CREDENTIAL_WORDS) else []
    undeclared = sorted(k for k in seen["kinds"] if not _mentions(description, DECLARES[k]))
    return StructuralFlags(
        flag_unmentioned_domain=bool(unmentioned),
        flag_credential_access=bool(creds),
        flag_undeclared_action_type=bool(undeclared),
        evidence={"unmentioned_hosts": unmentioned[:5], "credential_reads": creds[:5],
                  "undeclared_action_types": undeclared},
    )
