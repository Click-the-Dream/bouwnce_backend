const baseDir = __dirname;

module.exports = {
  apps: [
    {
      name: "staging",
      cwd: baseDir,
      script: "/bin/bash",
      args: '-lc \'${UV_BIN:-uv} run uvicorn main:app --host 0.0.0.0 --port 8000\'',
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "celery-worker-staging",
      cwd: baseDir,
      script: "/bin/bash",
      args: '-lc \'${UV_BIN:-uv} run celery -A app.worker.celery_app.celery_app worker --loglevel=info\'',
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "flower-staging",
      cwd: baseDir,
      script: "/bin/bash",
      args: '-lc \'${UV_BIN:-uv} run celery -A app.worker.celery_app.celery_app flower --port=5555\'',
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
