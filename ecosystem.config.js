const baseDir = __dirname;

module.exports = {
  apps: [
    {
      name: "staging",
      cwd: baseDir,
      script: "bin/start-api.sh",
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
      script: "bin/start-celery-worker.sh",
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
      script: "bin/start-flower.sh",
      autorestart: true,
      watch: false,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
