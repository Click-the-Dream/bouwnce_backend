#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$PROJECT_ROOT/.venv/bin/python" -m celery -A app.worker.celery_app.celery_app flower --port=5555
