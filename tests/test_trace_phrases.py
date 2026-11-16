"""Enriched trace-to-text: the phrase each kind of action becomes, and what is cut first.

test_trace_to_text.py covers the design rules; this file covers the rest of the phrase
table, one action at a time, so a changed template shows up as a named failure.
"""

import pytest

from divergence.preprocessing.structural_flags import compute_structural_flags
from divergence.preprocessing.trace_to_text import trace_to_enriched_text


def ev(action, target, status="ok", step=1):
    return {"action": action, "target": target, "status": status, "step": step}


@pytest.mark.parametrize("command, phrase", [
    ("sudo rm -rf /var/log", "Runs a command as administrator"),
    ("ssh root@203.0.113.9", "Connects to 203.0.113.9 over SSH"),
    ("base64 -d payload.b64", "Decodes base64-encoded data"),
    ("base64 notes.txt", "Encodes data as base64"),
    ("chmod +x run.sh", "Makes run.sh executable"),
    ("chmod 644 a.txt", "Changes file permissions"),
    ("crontab jobs.txt", "Schedules a recurring cron job"),
    ("useradd eve", "Changes user accounts or file ownership"),
    ("systemctl enable x.service", "Manages system services"),
    ("pkill python", "Stops other processes"),
    ("openssl enc -aes-256-cbc -in a", "Encrypts or decrypts data"),
    ("printenv", "Reads environment variables"),
    ("pip install requests flask", "Installs packages requests, flask"),
    ("python3 -m pip install somepkg", "Installs packages somepkg"),
    ("npm run build", "Uses the npm package manager"),
    ("npx cowsay hi", "Runs package cowsay with npx"),
    ("git clone https://gitlab.com/x/y.git", "Clones a repository from gitlab.com"),
    ("git status", "Uses git status"),
    ("python3 -c 'print(1)'", "Runs inline Python code"),
    ("bash", "Starts a shell"),
    ("python3 -m http.server", "Runs Python module http.server"),
    ("python3 tool.py", "Runs Python script tool.py"),
    ("./deploy.sh", "Runs script deploy.sh"),
    ("docker ps", "Uses the docker command-line tool"),
    ("tar -xzf a.tgz", "Archives or extracts files"),
    ("whoami", "Collects system information"),
    ("ls -la", "Lists files"),
    ("frobnicate --now", "Runs program frobnicate"),
    ("./xmrig -o pool", "Runs a cryptocurrency miner"),
    ("curl", "Makes a web request"),
    ("wget http://45.88.180.54/a.bin", "Downloads from raw IP address 45.88.180.54"),
    ("timeout 20 curl https://api.site.io/v1/rank/users", "Downloads from api.site.io (rank users)"),
])
def test_process_phrase(command, phrase):
    assert trace_to_enriched_text([ev("process_exec", command)]) == phrase


@pytest.mark.parametrize("command", ["cat a.txt", "node /usr/lib/node_modules/npm/bin/npm install"])
def test_plumbing_and_wrapper_processes_say_nothing(command):
    assert trace_to_enriched_text([ev("process_exec", command)]) == "Does nothing observable"


@pytest.mark.parametrize("event, phrase", [
    (ev("dns_lookup", "evil.example"), "Contacts domain evil.example"),
    (ev("web_fetch", "https://docs.site.org/x", "failed"), "Fetches web page docs.site.org (connection failed)"),
    (ev("network_connect", "8.8.8.8:53", "failed"), "Connects to raw IP address 8.8.8.8 on port 53 (connection failed)"),
    (ev("network_connect", "172.30.0.2:443"), "Connects to an external server on port 443"),   # the sinkhole
    (ev("file_search", "*.py in ."), "Searches for files"),
    (ev("file_read", "/root/.ssh/id_rsa", "failed"), "Reads credential file ~/.ssh/id_rsa (not found)"),
    (ev("file_read", "/workspace/skill/a.md"), "Reads its own skill files"),
    (ev("file_read", "/workspace/.opencode/config.json"), "Reads the agent's configuration"),
    (ev("file_read", "/tmp"), "Lists files"),
    (ev("file_read", "/root/notes/a.txt"), "Reads a file in ~/notes"),
    (ev("file_write", "/tmp/x.bin"), "Writes temporary file x.bin"),
    (ev("mystery_action", "x"), "Mystery action x"),                # unknown action types are kept, not dropped
])
def test_other_action_phrase(event, phrase):
    assert trace_to_enriched_text([event]) == phrase


def test_mass_delete_is_one_grouped_phrase():
    trace = [ev("file_delete", f"/workspace/proj/f{i}") for i in range(12)]
    assert trace_to_enriched_text(trace) == "Deletes 12 files in /workspace/proj"


def test_tool_command_is_described_only_when_its_processes_are_not():
    assert trace_to_enriched_text([ev("command", "curl https://a.example/x", step=5)]) == "Downloads from a.example"
    both = [ev("command", "python3 run.py", step=2), ev("process_exec", "python3 run.py", step=2)]
    assert trace_to_enriched_text(both) == "Runs Python script run.py"      # said once, not twice


def test_overlong_text_keeps_the_credential_read_and_stays_in_budget():
    trace = ([ev("process_exec", f"ls dir{i}") for i in range(3)]
             + [ev("process_exec", f"python3 script_number_{i:03d}_with_a_long_name.py") for i in range(40)]
             + [ev("file_read", "/root/.aws/credentials")])
    text = trace_to_enriched_text(trace)
    assert text == "Reads credential file ~/.aws/credentials"       # LOW, then MEDIUM phrases were dropped
    only_high = [ev("file_read", f"/root/.ssh/key_{i:03d}_{'x' * 40}") for i in range(40)]
    assert len(trace_to_enriched_text(only_high)) <= 900            # still too long: cut from the end


# --- structural flags: the two rule branches no other test reaches -------------------------

def test_a_host_written_out_in_full_counts_as_mentioned():
    trace = [ev("dns_lookup", "files.internal-corp.net")]
    assert not compute_structural_flags("Syncs notes with files.internal-corp.net.", trace).flag_unmentioned_domain
    assert compute_structural_flags("Formats markdown tables.", trace).flag_unmentioned_domain


def test_privilege_change_is_an_undeclared_action_type_unless_declared():
    trace = [ev("process_exec", "sudo apt-get update")]
    flags = compute_structural_flags("Formats markdown tables.", trace)
    assert flags.flag_undeclared_action_type and flags.evidence["undeclared_action_types"] == ["privilege"]
    assert not compute_structural_flags("Needs root to change system settings.", trace).flag_undeclared_action_type
