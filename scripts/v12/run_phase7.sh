#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="$ROOT/scripts/v12/phase7_context.sh"
TASKS="$ROOT/tasks/v12/phase7_context.json"
REGISTRY="$ROOT/docs/MODEL_REGISTRY_V12.md"

run_bucket() {
    bucket="$1"
    ctx="$2"

    echo
    echo "=========================================="
    echo " PHASE 7 — $bucket / context=$ctx"
    echo "=========================================="

    LMB_CONTEXT="$ctx" \
    LMB_REQUEST_TIMEOUT=7200 \
    "$RUNNER" \
      --registry "$REGISTRY" \
      --tasks "$TASKS" \
      --results-dir "$ROOT/results/v12/phase7/$bucket" \
      --task "ctx-$bucket-01" \
      --task "ctx-$bucket-02" \
      --task "ctx-$bucket-03"
}

run_bucket 8k 8192
run_bucket 16k 16384
run_bucket 32k 32768
run_bucket 64k 65536
