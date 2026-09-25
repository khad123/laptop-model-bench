#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

exec "$ROOT/instruction.sh" \
  --registry "$ROOT/docs/MODEL_REGISTRY_V12.md" \
  --tasks "$ROOT/tasks/v12/phase5_instruction.json" \
  --results-dir "$ROOT/results/v12/phase5" \
  "$@"
