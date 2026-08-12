# python-fastapi

A FastAPI backend built around a layered **Model → Repository → Service → Controller**
architecture, with cookie-based JWT authentication (access + rotating refresh tokens),
role/permission-based access control (RBAC), a Postgres database managed by Alembic
migrations, and a full unit + integration test suite. Everything runs through Docker.

## Project layout

```
main.py                         # FastAPI app instance; mounts the global auth dependency and includes routers
app/
  config.py                     # Settings (pydantic-settings, reads .env)
  database.py                   # async SQLAlchemy engine + AsyncSessionLocal session factory
  core/
    auth.py                     # @public marker, enforce_auth (global auth gate), get_current_user,
                                 #   require_role(...) / require_permission(...) RBAC dependencies
    dependencies.py             # DI providers: get_db_session, get_*_repository, get_*_service
    security.py                 # password hashing, JWT access tokens, refresh token hashing, auth cookies
  models/
    base.py                     # Base (DeclarativeBase), TimestampMixin
    user.py                     # User
    role.py                     # Role, Permission, role_permissions / user_roles association tables
    item.py                     # Item
    refresh_token.py            # RefreshToken
  repositories/
    base.py                     # BaseRepository[ModelType] — generic get_by_id/list/create/update/delete
    user_repository.py          # UserRepository
    role_repository.py          # RoleRepository
    refresh_token_repository.py # RefreshTokenRepository
    item_repository.py          # ItemRepository
  schemas/
    user.py                     # UserCreate, UserRead
    auth.py                     # LoginRequest
    item.py                     # ItemCreate, ItemUpdate, ItemRead
  services/
    auth_service.py             # AuthService — register/login/refresh/logout, domain errors
    item_service.py             # ItemService — list/get/create/update/delete, ItemNotFoundError
  routers/
    health.py                   # GET /health (public)
    auth.py                     # POST /auth/register, /auth/login, /auth/refresh, /auth/logout
    items.py                    # GET/POST/PATCH/DELETE /items
alembic/
  env.py                        # async-aware Alembic environment
  versions/                     # migrations: users, items, roles/permissions (+ seed), refresh_tokens
docker/
  init-test-db.sh               # creates the fastapi_test database when the db container first initializes
tests/
  unit/
    core/test_security.py       # hashing/JWT helpers, no DB, no app
    services/                   # AuthService/ItemService tests against in-memory fake repositories
  integration/
    conftest.py                 # httpx.AsyncClient against the real app, real Postgres test DB
    repositories/                # repository tests against a real Postgres session
    routers/                     # end-to-end router tests (auth, items, health, RBAC, app wiring)
Makefile                        # docker compose / alembic command aliases
requirements.txt
Dockerfile                      # development / production build stages
docker-compose.yml              # api + db (Postgres) services
alembic.ini
pytest.ini
.env.example
```

## Setup

Docker (OrbStack or Docker Desktop) must be running — there is no local virtualenv.

```bash
cp .env.example .env
make up            # == docker compose up --build
```

This builds the image, starts a Postgres container (`db`) and the API container (`api`),
and waits for Postgres to report healthy before starting the API. **Migrations run
automatically on container start** — the container's entrypoint runs `alembic upgrade head`
before starting `uvicorn` (see the `CMD` in `Dockerfile`), so a fresh checkout ends up with
an up-to-date schema (including the seeded roles/permissions from the migration described
below) with no manual step required.

The app is available at http://localhost:8000, with interactive docs at
http://localhost:8000/docs. The project directory is mounted into the container, so local
edits are picked up automatically by `--reload` in development.

Run `make up` in the foreground to see logs, or `make upd` to run detached (then `make logs`
to follow logs, `make down` to stop).

## Migrations

Migrations live in `alembic/versions/` and run automatically on container boot (see above),
but you'll generate and apply them by hand during development:

```bash
make makemigrations msg="add foo table"   # == docker compose exec api alembic revision --autogenerate -m "add foo table"
make migrate                              # == docker compose exec api alembic upgrade head
```

The full, non-aliased forms (useful if you want extra Alembic flags):

```bash
docker compose exec api alembic revision --autogenerate -m "add foo table"
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
docker compose exec api alembic history
```

The current migration chain creates `users`, `items`, `roles`/`permissions` (plus a
data migration that seeds them — see RBAC below), and `refresh_tokens`.

## Authentication

Auth is **cookie-based**, not bearer-token-based: `POST /auth/login` and `POST /auth/refresh`
set `httponly` `access_token` and `refresh_token` cookies (`app/core/security.py`), and every
subsequent request is authenticated by whatever is in the `access_token` cookie — there's no
`Authorization: Bearer ...` header to manage.

Every route is **private by default**. `app/core/auth.py` wires a single `enforce_auth`
dependency onto the whole API router in `main.py`; it inspects the matched endpoint for an
`__is_public__` flag (set by the `@public` decorator) and, if absent, requires a valid
`access_token` cookie for a still-active user before the request proceeds. Routes that should
be reachable without auth (e.g. `/health`, `/auth/register`, `/auth/login`, `/auth/refresh`,
`GET /items`, `GET /items/{id}`) are explicitly marked `@public`.

Example flow with a cookie jar:

```bash
# Register (public) — creates the user and assigns the default "user" role
curl -c cookies.txt -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email": "a@example.com", "password": "Passw0rd!"}'

# Log in (public) — sets access_token + refresh_token cookies
curl -c cookies.txt -b cookies.txt -X POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email": "a@example.com", "password": "Passw0rd!"}'

# Create an item (private — any authenticated user)
curl -b cookies.txt -X POST localhost:8000/items -H 'Content-Type: application/json' \
  -d '{"name": "Widget"}'

# Rotate the refresh token (public endpoint, but reads the refresh_token cookie) —
# issues a new access/refresh pair and revokes the old refresh token
curl -c cookies.txt -b cookies.txt -X POST localhost:8000/auth/refresh

# Log out (private) — revokes the refresh token and clears both cookies
curl -b cookies.txt -X POST localhost:8000/auth/logout
```

`POST /auth/register` returns the created user (`UserRead`: `id`, `email`, `is_active`) with
`201`. `POST /auth/login`/`/auth/refresh`/`/auth/logout` return a small `{"detail": "..."}`
body — the interesting part of the response is the `Set-Cookie` headers.

Refresh tokens are stored server-side only as a SHA-256 hash (`refresh_tokens.token_hash`);
reusing an already-revoked refresh token revokes every refresh token for that user
(`AuthService.refresh` in `app/services/auth_service.py`) as a reuse-detection safeguard.

## RBAC

Roles and permissions are seeded by a data migration
(`alembic/versions/895ca4909c8a_seed_roles_and_permissions.py`):

- Roles: `user` (assigned to every new registration by `AuthService.register`), `admin`
- Permissions: `items:write`, `items:delete` — both granted to the `admin` role

`app/core/auth.py` exposes two dependency factories on top of `get_current_user`:

- `require_role(role_name)` — 403s unless the current user has that role
- `require_permission(permission_name)` — 403s unless one of the current user's roles grants
  that permission

`app/routers/items.py`'s `DELETE /items/{item_id}` is the concrete example — it's gated with
`Depends(require_permission("items:delete"))`, so only a user with the `admin` role (the only
role currently granted that permission) can delete an item:

```python
@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    user: User = Depends(require_permission("items:delete")),
    service: ItemService = Depends(get_item_service),
) -> None:
    ...
```

`POST /items` and `PATCH /items/{item_id}` only require an authenticated user (`get_current_user`) —
they are not currently gated behind the seeded `items:write` permission.

## Testing

```bash
make test    # == docker compose exec api pytest
```

Use `docker compose run --rm api pytest ...` instead if the container isn't already running.
Run a single file or test the same way as plain `pytest`, e.g.:

```bash
docker compose exec api pytest tests/integration/routers/test_rbac.py
docker compose exec api pytest tests/integration/routers/test_rbac.py::test_delete_with_admin_permission_succeeds
```

- **`tests/unit/`** — no database, no running app. `tests/unit/services/fakes.py` provides
  in-memory fake repositories (plain dataclasses + dicts) that `AuthService`/`ItemService` are
  constructed against directly, and `tests/unit/core/test_security.py` exercises the hashing/JWT
  helpers in isolation.
- **`tests/integration/`** — a real Postgres test database (`fastapi_test`, created by
  `docker/init-test-db.sh` when the `db` container first initializes, pointed to by
  `TEST_DATABASE_URL`). `tests/integration/conftest.py` builds the schema once per test session,
  then wraps each individual test in a transaction/savepoint that's rolled back afterwards so
  tests stay isolated without re-migrating between tests. Router tests drive the real app
  through `httpx.AsyncClient` (with cookie-jar behavior, exactly like a real client) rather than
  calling services directly.

## Make targets

| Target | Runs | Purpose |
| --- | --- | --- |
| `make up` | `docker compose up --build` | Build and start `db` + `api` in the foreground (logs streamed) |
| `make upd` | `docker compose up -d --build` | Same, but detached |
| `make down` | `docker compose down` | Stop and remove the containers |
| `make test` | `docker compose exec api pytest` | Run the full test suite inside the running `api` container |
| `make migrate` | `docker compose exec api alembic upgrade head` | Apply all pending migrations |
| `make makemigrations msg="..."` | `docker compose exec api alembic revision --autogenerate -m "$(msg)"` | Autogenerate a new migration from model changes |
| `make logs` | `docker compose logs -f api` | Follow the `api` container's logs |
| `make shell` | `docker compose exec api bash` | Open a shell inside the running `api` container |

## Building the production image directly

```bash
docker build --target production -t python-fastapi .
docker run -p 8000:8000 --env-file .env python-fastapi
```

The `production` stage's `CMD` already runs `alembic upgrade head` before starting `uvicorn`
(same as `development`), so migrations are applied automatically as the container starts —
no separate manual `alembic upgrade head` step is needed as long as the container can reach
the database in `DATABASE_URL`. If you do want to run migrations as a distinct, explicit step
(e.g. in a deploy pipeline, ahead of rolling out new containers), you can still do so directly:

```bash
docker run --env-file .env python-fastapi alembic upgrade head
```
