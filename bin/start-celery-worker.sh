#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# concurrency=1: single worker process to minimize Redis connections.
# On Upstash Free plan (10 connections), each Celery fork uses 2+ connections,
# so we run only 1 fork to leave room for API + WebSocket connections.
# --pool=solo: required for asyncio tasks. The default prefork pool forks
# child processes, which breaks asyncio event loops created before the fork.
# Solo runs tasks in the main process (no forking), so asyncio.run() works.
exec "$PROJECT_ROOT/.venv/bin/python" -m celery -A app.worker.celery_app.celery_app worker --loglevel=info --concurrency=1 --pool=solo
