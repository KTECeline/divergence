#!/usr/bin/env bash
# entrypoint_direct.sh — Stage 3 direct-execution trace collector.
#
# Runs the skill's declared workflow with NO agent in the loop, so the skill's
# runtime behaviour is observable even when the agent would have refused. The
# skill's "payload" is usually not a loose script file run with no arguments —
# it is the shell commands written in SKILL.md (e.g. `python3 scripts/x.py list`
# or an inline `curl ... | python3 -c "..."`). So this runs the shell command
# blocks documented in SKILL.md, which is what the agent would have executed.
#
# Containment is unchanged from the agent entrypoint: sealed dvg-isolated
# network (no route to the internet or host), caps dropped; every network
# attempt lands on INetSim and is logged, not delivered. Evidence is written to
# the same files Core/verification/sandbox.py._collect_evidence parses.
#
# All working files are kept FLAT in /tmp/evidence (no sub-directory): the host
# user owns that mounted dir and can delete flat root-owned files on cleanup,
# but cannot delete the contents of a root-owned SUB-directory. They all begin
# with "_" and live under /tmp/evidence, which the normaliser treats as noise.
set -u

EVIDENCE_DIR="/tmp/evidence"
TIMEOUT="${EXEC_TIMEOUT:-90}"             # overall cap for the whole workflow
PER_CMD="${DVG_PER_SCRIPT_TIMEOUT:-20}"   # cap per command block (while-True payloads, hangs)
SKILL_SRC="/workspace/skill"
WORK="/workspace/run"

mkdir -p "$EVIDENCE_DIR" "$WORK"
cp -r "$SKILL_SRC"/. "$WORK"/ 2>/dev/null || true
if [ -d "$WORK/scripts" ]; then chmod +x "$WORK/scripts/"* 2>/dev/null || true; fi

# ---- filesystem monitoring (same as the agent entrypoint) ----------------
inotifywait -mr --timefmt '%Y-%m-%dT%H:%M:%S' --format '%T %w%f %e' \
    --exclude '^/tmp/evidence/' \
    /root /workspace /etc/ /tmp/ 2>/dev/null \
    > "$EVIDENCE_DIR/inotify.log" 2>&1 &
INOTIFY_PID=$!
sleep 0.3

# ---- extract the runnable shell blocks from SKILL.md ---------------------
# Fenced ``` / ~~~ blocks whose language is a shell (bash/sh/shell/zsh/console)
# hold the actual invocations and inline payloads. ```python blocks are source
# listings or infinite-loop monitors, so they are NOT auto-run. Each block goes
# to its own flat _cmd_NNN.sh so one block's `cd` can't affect the next.
SKILL_MD="$WORK/SKILL.md"
[ -f "$SKILL_MD" ] || SKILL_MD=$(find "$WORK" -maxdepth 2 -iname 'SKILL.md' | head -1)
if [ -n "${SKILL_MD:-}" ] && [ -f "$SKILL_MD" ]; then
  awk -v dir="$EVIDENCE_DIR" '
    /^(```|~~~)/ {
      if (inblock) { inblock=0; close(f); next }
      lang=$0; sub(/^(```|~~~)/,"",lang); gsub(/[ \t`]/,"",lang); lang=tolower(lang)
      if (lang=="bash"||lang=="sh"||lang=="shell"||lang=="zsh"||lang=="console") {
        inblock=1; n++; f=sprintf("%s/_cmd_%03d.sh", dir, n)
      }
      next
    }
    inblock { line=$0; sub(/^\$ /,"",line); print line > f }
  ' "$SKILL_MD"
fi

# Fallback: no documented shell blocks, but the skill ships scripts -> run them
# bare, so a scripts-only skill still produces a trace.
if ! ls "$EVIDENCE_DIR"/_cmd_*.sh >/dev/null 2>&1; then
  i=0
  while IFS= read -r s; do
    i=$((i+1)); f=$(printf '%s/_cmd_%03d.sh' "$EVIDENCE_DIR" "$i"); d=$(dirname "$s"); b=$(basename "$s")
    case "$b" in
      *.py) printf "cd '%s' && python3 '%s'\n" "$d" "$b" > "$f" ;;
      *.sh) printf "cd '%s' && bash '%s'\n"    "$d" "$b" > "$f" ;;
    esac
  done < <(find "$WORK" -type f \( -name '*.py' -o -name '*.sh' \) | sort)
fi

# ---- build one driver that runs every block, isolated, from the skill dir -
DRIVER="$EVIDENCE_DIR/_driver.sh"
{
  echo '#!/usr/bin/env bash'
  for f in $(ls "$EVIDENCE_DIR"/_cmd_*.sh 2>/dev/null | sort); do
    echo "cd '$WORK' 2>/dev/null"
    echo "timeout ${PER_CMD} bash '$f' </dev/null >>'$EVIDENCE_DIR/_script_stdout.log' 2>>'$EVIDENCE_DIR/_script_stderr.log' || true"
  done
} > "$DRIVER"
chmod +x "$DRIVER"

: > "$EVIDENCE_DIR/agent_output.json"   # no agent in direct mode
ls "$EVIDENCE_DIR"/_cmd_*.sh >/dev/null 2>&1 && cat "$EVIDENCE_DIR"/_cmd_*.sh > "$EVIDENCE_DIR/commands_run.txt"

# ---- run under one strace ------------------------------------------------
strace -f -y -s 256 \
    -e trace=network,file,process \
    -o "$EVIDENCE_DIR/strace.log" \
    timeout "$TIMEOUT" bash "$DRIVER" \
    2> "$EVIDENCE_DIR/stderr.log" || true
echo $? > "$EVIDENCE_DIR/exit_code"

# Fold the per-command stderr into stderr.log so it is collected into the
# result (result["stderr"]) and persisted to Logs/runtime/, making script
# errors (ModuleNotFoundError, FileNotFoundError, usage/arg errors) visible.
{ echo "=== script stderr ==="; cat "$EVIDENCE_DIR/_script_stderr.log" 2>/dev/null; } >> "$EVIDENCE_DIR/stderr.log"

kill "$INOTIFY_PID" 2>/dev/null || true
wait "$INOTIFY_PID" 2>/dev/null || true
# Make every file removable by the host user on cleanup (flat files only).
chmod 666 "$EVIDENCE_DIR"/* 2>/dev/null || true
echo "Direct evidence collection complete."
