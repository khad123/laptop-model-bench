#!/usr/bin/env bash
set -euo pipefail

if ! command -v bwrap >/dev/null 2>&1; then
  echo "FAIL: bubblewrap (bwrap) is not installed." >&2
  exit 2
fi
if [[ ! -x /usr/bin/python3 ]]; then
  echo "FAIL: /usr/bin/python3 is not available." >&2
  exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/test_runner.py" <<'PY'
import importlib.util
import json
import socket

spec = importlib.util.spec_from_file_location("candidate", "/work/candidate.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

result = mod.add_one(41)
if result != 42:
    print(json.dumps({"status": "test_failure", "expected": 42, "got": result}))
    raise SystemExit(1)

interfaces = [name for _, name in socket.if_nameindex()]
non_loopback = [name for name in interfaces if name != "lo"]
if non_loopback:
    print(json.dumps({"status": "network_namespace_failure", "interfaces": interfaces}))
    raise SystemExit(3)

print(json.dumps({"status": "pass", "result": result, "interfaces": interfaces}))
PY

sandbox_cmd() {
  local -a cmd=(
    bwrap
    --die-with-parent
    --new-session
    --unshare-net
    --unshare-pid
    --unshare-ipc
    --unshare-uts
    --ro-bind /usr /usr
  )

  for path in /lib /lib64 /etc; do
    if [[ -e "$path" || -L "$path" ]]; then
      cmd+=(--ro-bind "$path" "$path")
    fi
  done

  cmd+=(
    --dev /dev
    --proc /proc
    --tmpfs /tmp
    --bind "$WORK" /work
    --chdir /work
    /usr/bin/python3 -I /work/test_runner.py
  )

  printf '%q ' "${cmd[@]}"
}

run_sandbox() {
  local cmd_text
  cmd_text="$(sandbox_cmd)"
  (
    ulimit -t 3
    ulimit -v $((768 * 1024))
    ulimit -f 8192
    ulimit -n 64
    eval "$cmd_text"
  )
}

echo "Phase 3 sandbox self-test"
echo "1/2: known-good code should PASS and expose no non-loopback network interface"
cat >"$WORK/candidate.py" <<'PY'
def add_one(x):
    return x + 1
PY

if ! GOOD_OUTPUT="$(run_sandbox 2>&1)"; then
  echo "FAIL: known-good sandbox execution failed:" >&2
  echo "$GOOD_OUTPUT" >&2
  exit 2
fi
echo "$GOOD_OUTPUT"

echo "2/2: known-bad code should be rejected by its tests"
cat >"$WORK/candidate.py" <<'PY'
def add_one(x):
    return x
PY

set +e
BAD_OUTPUT="$(run_sandbox 2>&1)"
BAD_RC=$?
set -e
if [[ $BAD_RC -eq 0 ]]; then
  echo "FAIL: known-bad code unexpectedly passed." >&2
  echo "$BAD_OUTPUT" >&2
  exit 2
fi
echo "$BAD_OUTPUT"

echo "PASS: bubblewrap execution, test failure detection, and isolated network namespace are working."
