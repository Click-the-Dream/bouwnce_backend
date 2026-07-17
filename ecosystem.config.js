const baseDir = __dirname;

module.exports = {
  apps: [
    {
      name: "staging",
      cwd: baseDir,
      script: "bin/start-api.sh",
      interpreter: "bash",
      autorestart: true,
      watch: false,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "production-api",
      cwd: baseDir,
      script: "bin/start-api.sh",
      interpreter: "bash",
      autorestart: true,
      watch: false,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
