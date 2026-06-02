#!/usr/bin/env bash
set -euo pipefail

UV_BIN="${UV_BIN:-/home/ubuntu/.local/bin/uv}"
exec "$UV_BIN" run celery -A app.worker.celery_app.celery_app flower --port=5555
