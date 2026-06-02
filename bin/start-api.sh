#!/usr/bin/env bash
set -euo pipefail

UV_BIN="${UV_BIN:-/home/ubuntu/.local/bin/uv}"
exec "$UV_BIN" run uvicorn main:app --host 0.0.0.0 --port 8000
