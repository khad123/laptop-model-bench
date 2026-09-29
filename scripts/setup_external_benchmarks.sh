#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/bench-tools"
REPOS="$TOOLS/repos"
mkdir -p "$REPOS"
export UV_CACHE_DIR="$TOOLS/.uv-cache"
export UV_HTTP_RETRIES="${UV_HTTP_RETRIES:-10}"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-60}"

if ! command -v uv >/dev/null 2>&1; then
  printf 'uv is required. Install uv, then rerun this script.\n' >&2
  exit 2
fi
if ! command -v git >/dev/null 2>&1; then
  printf 'git is required. Install git, then rerun this script.\n' >&2
  exit 2
fi

checkout_pinned() {
  local name="$1" target="$2"
  local repo_url revision current
  repo_url="$(python3 - "$ROOT/scripts/external_benchmark_revisions.json" "$name" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]["remote"])
PY
)"
  revision="$(python3 - "$ROOT/scripts/external_benchmark_revisions.json" "$name" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]["revision"])
PY
)"
  if [[ ! -d "$target/.git" ]]; then
    mkdir -p "$target"
    git -C "$target" init -q
    git -C "$target" remote add origin "$repo_url"
  fi
  current="$(git -C "$target" rev-parse HEAD 2>/dev/null || true)"
  if [[ "$current" != "$revision" ]]; then
    git -C "$target" fetch --depth 1 origin "$revision"
    git -C "$target" checkout --detach FETCH_HEAD
  fi
}

make_env() {
  local name="$1" repo="$2" extra="${3:-}"
  local env="$TOOLS/$name/.venv"
  if [[ ! -x "$env/bin/python" ]]; then
    uv venv --python python3.14 "$env"
  fi
  if [[ -n "$extra" ]]; then
    (cd "$repo" && uv pip install --python "$env/bin/python" -e ".[$extra]")
  else
    uv pip install --python "$env/bin/python" -e "$repo"
  fi
}

EVALPLUS="$REPOS/evalplus"
LLM_BENCH="$REPOS/llm-benchmark"
LM_EVAL="$REPOS/lm-evaluation-harness"
checkout_pinned evalplus "$EVALPLUS"
checkout_pinned llm-benchmark "$LLM_BENCH"
checkout_pinned lm-evaluation-harness "$LM_EVAL"

make_env evalplus "$EVALPLUS"
make_env llm-benchmark "$LLM_BENCH"
make_env lm-evaluation-harness "$LM_EVAL" api

uv pip freeze --python "$TOOLS/evalplus/.venv/bin/python" > "$TOOLS/evalplus/requirements-installed.txt"
uv pip freeze --python "$TOOLS/llm-benchmark/.venv/bin/python" > "$TOOLS/llm-benchmark/requirements-installed.txt"
uv pip freeze --python "$TOOLS/lm-evaluation-harness/.venv/bin/python" > "$TOOLS/lm-evaluation-harness/requirements-installed.txt"

export XDG_CACHE_HOME="$TOOLS/cache"
"$TOOLS/evalplus/.venv/bin/python" -c \
  'from evalplus.data.humaneval import _ready_human_eval_plus_path; print("Cached HumanEval+ at:", _ready_human_eval_plus_path())'

python3 - "$TOOLS/tool-versions.json" "$EVALPLUS" "$LLM_BENCH" "$LM_EVAL" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

target = Path(sys.argv[1])
projects = {
    "evalplus": Path(sys.argv[2]),
    "llm-benchmark": Path(sys.argv[3]),
    "lm-evaluation-harness": Path(sys.argv[4]),
}
versions = {}
for name, repo in projects.items():
    rev = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    versions[name] = {"path": str(repo), "revision": rev, "remote": subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()}
target.write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")
print(f"Recorded source revisions in {target}")
PY

LLAMA_BIN="${LLAMA_CPP_BIN:-$HOME/Models/llama.cpp-k2-current/build/bin}"
for binary in "$LLAMA_BIN/llama-bench" "$LLAMA_BIN/llama-server"; do
  if [[ ! -x "$binary" ]]; then
    printf 'Missing executable: %s\n' "$binary" >&2
    exit 2
  fi
done

for pair in \
  "evalplus:$TOOLS/evalplus/.venv/bin/evalplus.codegen" \
  "llm-benchmark:$TOOLS/llm-benchmark/.venv/bin/llm-bench" \
  "lm-eval:$TOOLS/lm-evaluation-harness/.venv/bin/lm_eval"; do
  name="${pair%%:*}"
  binary="${pair#*:}"
  if [[ ! -x "$binary" ]]; then
    printf 'Install did not create %s: %s\n' "$name" "$binary" >&2
    exit 2
  fi
  printf 'Ready: %s\n' "$name"
done
printf 'Ready: llama-bench (%s)\n' "$LLAMA_BIN/llama-bench"
printf '\nSetup complete. No models were loaded or benchmarked.\n'
printf 'EvalPlus scoring requires Docker to be running and accessible when you start a benchmark.\n'
