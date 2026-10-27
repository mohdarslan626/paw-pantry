# Future improvements

Lower-priority items identified during the standardization/security review,
intentionally not implemented now (see `README.md` for what was done).

## Testing

- Tests currently require a live Postgres `paw_pantry_test` database with no
  fallback. Add a disposable/testcontainers-based or SQLite-compatible path
  so tests can run without manual DB setup.
- No integration tests exist for the `orders` and `addresses` routers despite
  both being implemented — add coverage.
- No frontend tests at all. Add component tests (Vitest + Testing Library)
  and at least a smoke end-to-end test (Playwright) for the login ->
  browse -> add to cart -> checkout flow.
- No coverage threshold/reporting wired into a pipeline.

## CI/CD

- No `.github/workflows` (or equivalent) exists. Add a pipeline that runs
  backend lint/type-check/tests and frontend lint/build/tests on every PR,
  and ideally builds the two Docker images to catch Dockerfile breakage
  early.

## Backend

- No lint/format/type-check tooling (ruff, black, mypy) configured.
- No rate limiting (e.g. slowapi + Redis) on auth or checkout endpoints.
- Logging is minimal (basic `logging.basicConfig`) — no structured
  (JSON) logs, no correlation/request IDs, no shipping to an aggregator.
- No dependency-vulnerability scanning (e.g. `pip-audit`, Dependabot).

## Frontend

- `App.tsx` is a single ~1100-line component holding auth, cart, checkout,
  and order-history state. Should be split into routed pages/components with
  a proper state layer (React Router + Context or a small state library).
- ESLint is configured but not type-aware (`recommendedTypeChecked` /
  `strictTypeChecked` are not enabled). No Prettier.
- Access token is stored in `localStorage`; migrating to an httpOnly cookie
  (with CSRF protection) would reduce XSS-driven token theft risk, but
  requires backend session/cookie support — a deliberate, separate change.

## Infrastructure

- No monorepo tooling (Turborepo/Nx) — backend and frontend are two
  hand-wired sibling trees. Fine at current size; revisit if more
  services/packages are added.
- No `LICENSE` file — add one if/when this repository is published
  externally.
