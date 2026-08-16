# Project Setup and Architecture

## Overview

This project is a **BOUNWCE BACKEND API** using PostgreSQL, MongoDB, and Redis Databases. The project follows a **layered architecture** to separate concerns and maintain modularity, making it easy for team development and maintenance.

The project also uses **`uv`** as the Python package manager and several Python tools for code quality, formatting, and migrations.

---

# Project Setup and Architecture

<!-- Badges -->

![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-15-blue?logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/mongodb-6.0-green?logo=mongodb&logoColor=white)
![Redis](https://img.shields.io/badge/redis-7.0-orange?logo=redis&logoColor=white)
![Code Quality](https://img.shields.io/badge/code%20quality-A%2B-brightgreen)

---

## Table of Contents

- [Python Package Manager](#python-package-manager)
- [Python Tools](#python-tools)
- [Databases](#databases)
- [Folder Structure](#folder-structure)
- [Running the Application](#running-the-application)
- [Database Migrations](#database-migrations)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Notes](#notes)

---

## Python Package Manager

The project uses **`uv`** as the package manager.

### Installing dependencies

```bash
uv install
```

This will install all dependencies listed in uv.lock.

---

### Running scripts

- To add a new package:

```bash
uv add <package_name>
```

- To add package to development

```bash
uv add <package_name> --dev
```

- To sync you environment with the application

```bash
uv sync
```

- To remove a package:

```bash
uv remove <package_name>

```

- To update dependencies:

```bash
uv update
```

---

### Python Tools

The project uses the following Python tools:

- **Black**: For automatic code formatting.

```bash
uv run black .

```

- **Ruff**: For linting and code quality checks.

```bash
ruff check .
```

- **Alembic**: For PostgreSQL database migrations.

```bash
uv run alembic upgrade head
```

- **Pre-commit**: To enforce code quality before commits.

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Whenever you want to commit, ruff and black will run, if they pass, you commit will become successful otherwise it will fail, ruff will automatically fix the issues, all you might want to do is

```bash
git add .
git commit -m "You commit message"
```

### Databases

This Projct uses three databases:

1. **PostgreSQL**
   - Used for relational, schema-based storage.
   - Migrations handles via **Alembic**
   - Connection via **SQLAlchemy**
2. **MongoDB**
   - Used for schema-less document storage.
   - Supports transactions via **client sessions**
   - Migration will be handled via custom Python scripts under `migrations/mongodb`
3. **Redis**
   - Used for caching and ephemeral data
   - Connection via a **Redis URL**
   - Long-lived client, dependency-injection via **FastAPI**

---

### Folder Structure

The project follows a **layered architecture**:

```graphql
├── Alembic
│   ├── env.py                   # Alembic environment configuration
│   ├── README                   # Alembic instructions
│   ├── script.py.mako           # Alembic template script
│   └── versions                 # Auto-generated migration scripts
├── alembic.ini                   # Alembic configuration
├── app
│   ├── api                       # API layer
│   │   ├── dependencies.py       # FastAPI dependency injection
│   │   └── v1                    # API versioning
│   │       └── __init__.py
│   ├── core                      # Core configuration and utilities
│   │   ├── config.py             # Environment configuration
│   │   ├── logging.py            # Logging configuration
│   │   └── security.py           # Security utilities (JWT, hashing)
│   ├── db                        # Database connections
│   │   ├── mongo.py              # MongoDB client and session
│   │   ├── postgres.py           # PostgreSQL engine and session
│   │   └── redis.py              # Redis client
│   ├── email_templates           # Email templates for notifications
│   ├── main.py                   # FastAPI application entry point
│   ├── models                    # SQLAlchemy ORM models
│   ├── schemas                   # Pydantic schemas for request/response
│   ├── service                   # Business logic layer
│   ├── test                      # Unit and integration tests
│   └── utils                     # Utility functions
├── main.py                       # Project entry point
├── migrations                    # Project-specific migrations
│   ├── __init__.py
│   ├── mongodb                   # MongoDB migration scripts
│   └── postgres
│       └── Alembic -> ../../Alembic  # Symlink to Alembic migrations
├── pyproject.toml                # Python project configuration
├── README.md                     # Project setup documentation
└── uv.lock                       # Dependency lockfile managed by uv
```

---

### Running the Application

1. Install dependencies

```bash
uv install
```

2. Run database migrations
   - **PostgreSQL**:

   ```bash
   uv run alembic upgrade head
   ```

   - **MongoDB**:

   ```bash
   python migrations/mongodb/<migration_script>.py
   ```

---

### Database Migrations

- PostgreSQL:
  - Handled using Alembic.

  - Migration scripts are under Alembic/versions.

  - Use alembic revision --autogenerate -m "description" to create migrations.

- MongoDB:
  - Managed via Python scripts in migrations/mongodb.

  - Supports versioning by numbering scripts (e.g., 001_add_field.py).

- Redis:
  - Redis does not require migrations; used for caching only.

---

### Pre-commit Hooks

- **Setup**

```bash
pre-commit install
```

- **Run manually**

```bash
pre-commit run --all-files
```

Ensures **code formatting, linting, and other checks** before commits.

---

### Notes

- Environment variables are configured in `app/core/config.py`.

- Use the **layered architecture** to maintain separation of concerns:
  - **API layer**: Handles HTTP requests and dependency injection.

  - **Service layer**: Contains business logic.

  - **DB layer**: Database connections and session management.

  - **Core layer**: Config, security, logging, utilities.

  - **Schemas**: Pydantic models for data validation.

- Logging and security utilities are centralized in `app/core`.

- Unit tests are placed under `app/test`.

---

### Web Push Notifications

The backend supports standard **Web Push** (VAPID + encrypted payloads) so browsers can
receive notifications even when the app is closed.

**Setup**

1. Generate VAPID keys (one-time, per environment):

   ```bash
   .venv/bin/python - <<'EOF'
   import base64
   from py_vapid import Vapid01
   v = Vapid01(); v.generate_keys()
   def b64url(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
   nums = v.public_key.public_numbers()
   pub = b64url(b'\x04' + nums.x.to_bytes(32, 'big') + nums.y.to_bytes(32, 'big'))
   priv = b64url(v.private_key.private_numbers().private_value.to_bytes(32, 'big'))
   print('VAPID_PUBLIC_KEY=' + pub)
   print('VAPID_PRIVATE_KEY=' + priv)
   EOF
   ```

2. Set in `.env`:

   ```
   VAPID_PUBLIC_KEY="..."
   VAPID_PRIVATE_KEY="..."
   VAPID_SUBJECT="mailto:ops@bouwnce.com"
   ```

**API endpoints**

| Method | Path                            | Auth | Purpose                            |
| ------ | ------------------------------- | ---- | ---------------------------------- |
| GET    | `/api/v1/push/vapid-public-key` | No   | VAPID public key for `subscribe()` |
| POST   | `/api/v1/push/subscribe`        | Yes  | Store a browser subscription       |
| DELETE | `/api/v1/push/subscribe`        | Yes  | Remove a browser subscription      |
| POST   | `/api/v1/push/test`             | Yes  | Send a test push (dev only)        |

Subscribe request body (the browser `PushSubscription`):

```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": { "p256dh": "...", "auth": "..." },
  "expirationTime": null
}
```

**Delivery pipeline**

- Events emitted with `PushNotificationEvent` (chat, matches, orders, payments) are
  persisted and pushed onto the Redis list `notifications:push:queue`.
- A **Celery beat** task (`app.worker.tasks.web_push.drain_push_queue`) drains that queue
  every 5 seconds and sends encrypted pushes to the user's web subscriptions.
- Expired subscriptions (HTTP 404/410 from the push service) are removed automatically.

Run the worker **and** beat to deliver pushes:

```bash
./bin/start-celery-worker.sh
./bin/start-celery-beat.sh
```

**Client side (frontend)**

For localhost development a demo page is served by the backend at `/push-demo`
(`/static/push-demo.html`), including `sw.js` and `manifest.json`. In production the
**frontend origin must host its own service worker** and call:

```js
const sub = await reg.pushManager.subscribe({
  userVisibleOnly: true,
  applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
});
fetch("/api/v1/push/subscribe", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify(sub.toJSON()),
});
```

---

### References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pymongo Documentation](https://pymongo.readthedocs.io/)]
- [Redis-Py Documentation](https://pypi.org/project/redis/)
- [UV Package Manager](https://uv-pm.org/)
