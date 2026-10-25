# Paw Pantry

Backend API and web frontend for a dog-food store: catalog (brands, categories,
products, variants, inventory), auth, cart, checkout/orders, and addresses.

- **Backend**: FastAPI + SQLAlchemy 2.x + PostgreSQL, Alembic migrations, JWT auth.
- **Frontend**: React 19 + Vite + TypeScript.

## Architecture

```
paw-pantry/
├── app/              FastAPI app (routers -> services -> repositories -> models)
├── alembic/          Database migrations
├── scripts/          One-off/dev scripts (e.g. product seeding)
├── tests/            Pytest suite (requires a live Postgres test DB)
├── frontend/         React + Vite SPA
├── Dockerfile         Backend image (uv + Python 3.12, non-root)
├── entrypoint.sh       Backend container entrypoint (migrate -> seed -> serve)
├── frontend/Dockerfile Frontend image (Vite build -> nginx, non-root)
└── docker-compose.yml  db + backend + frontend services
```

## Quick start (Docker)

Requires Docker and Docker Compose.

1. Copy the env file and fill in real values (at minimum, pick a real
   `POSTGRES_PASSWORD` and a long random `JWT_SECRET_KEY`):

   ```bash
   cp .env.example .env
   ```

2. Build and start everything:

   ```bash
   docker compose up --build
   ```

3. Services:

   | Service  | URL                              |
   |----------|-----------------------------------|
   | Frontend | http://localhost:5173              |
   | Backend  | http://localhost:8000 (docs at `/docs`) |
   | Postgres | localhost:5432                     |

   On first start, the backend container runs `alembic upgrade head`, then
   seeds a small set of demo products (idempotent — safe to restart; set
   `SEED_ON_STARTUP=false` in `.env` to skip), then starts `uvicorn`.

## Manual (non-Docker) setup

### Backend

Requires Python 3.12 and a running PostgreSQL instance, and
[uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env            # fill in DATABASE_URL / JWT_SECRET_KEY
uv sync                         # creates .venv, installs locked deps
uv run alembic upgrade head
uv run python -m scripts.seed_products   # optional: demo data
uv run uvicorn app.main:app --reload
```

Run tests (needs a separate `paw_pantry_test` database, `TEST_DATABASE_URL`
pointed at it):

```bash
uv run pytest
```

### Frontend

Requires Node.js 20 (see `frontend/.nvmrc`).

```bash
cd frontend
cp .env.example .env            # VITE_API_BASE_URL, defaults to localhost:8000
npm ci
npm run dev
```

## Environment variables

| Variable                      | Used by  | Purpose                                             |
|--------------------------------|----------|------------------------------------------------------|
| `POSTGRES_PASSWORD`            | db       | Postgres superuser-equivalent app password            |
| `DATABASE_URL`                 | backend  | SQLAlchemy connection string                          |
| `JWT_SECRET_KEY`                | backend  | Secret used to sign/verify access tokens              |
| `JWT_ALGORITHM`                 | backend  | JWT signing algorithm (default `HS256`)               |
| `ACCESS_TOKEN_EXPIRE_MINUTES`   | backend  | Access token lifetime (default `30`)                  |
| `CORS_ALLOWED_ORIGINS`          | backend  | Comma-separated list of allowed browser origins        |
| `SEED_ON_STARTUP`               | backend  | Run the idempotent demo-data seed script on boot       |
| `VITE_API_BASE_URL`             | frontend | Base URL the SPA calls for the API                     |

## Security notes

- CORS origins are environment-driven (`CORS_ALLOWED_ORIGINS`), not hardcoded.
- Passwords are hashed with `pwdlib` (argon2); JWTs are signed with
  `JWT_SECRET_KEY`, which must never be committed — `.env` is gitignored and
  `.env.example` only contains placeholders.
- The backend returns sanitized error bodies (no stack traces) for unhandled
  exceptions, and sets basic hardening headers (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`).
- Both Docker images run as non-root users.
- The access token is currently stored in the browser's `localStorage` (see
  `FUTURE_IMPROVEMENTS.md` for the httpOnly-cookie migration this should move
  to eventually).
- No `LICENSE` file is included (internal/assessment project). Add one before
  publishing this repository externally.

See [`FUTURE_IMPROVEMENTS.md`](./FUTURE_IMPROVEMENTS.md) for lower-priority
items identified during this review (testing, CI/CD, frontend architecture,
observability, rate limiting, etc.) that were intentionally not addressed now.
