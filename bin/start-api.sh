#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec "$PROJECT_ROOT/.venv/bin/python" -m uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --ws-ping-interval 45 \
  --ws-ping-timeout 90 \
  --timeout-keep-alive 75
