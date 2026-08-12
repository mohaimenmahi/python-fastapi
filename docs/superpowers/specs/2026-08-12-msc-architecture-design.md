# Model-Service-Controller Architecture Design

Date: 2026-08-12

## Goal

Reshape the currently near-empty FastAPI scaffold into a layered backend architecture:
Model → Repository → Service → Controller, with dependency injection, a global
authentication gate (private-by-default), an ORM with schema migrations, and a test
suite that supports both isolated unit tests and real-database integration tests.

Two vertical slices are built as concrete examples of the pattern: `User` (backs
authentication) and `Item` (a plain business resource, public reads / private writes).

## Non-goals

- No frontend, no session/cookie-based auth, no refresh-token rotation, no
  role/permission system beyond "authenticated or not" — those are extensions to a
  future spec, not part of this scaffold.
- No `dependency-injector`-style container library — constructor injection plus
  FastAPI's `Depends()` is sufficient (see "Dependency Injection" below).

## Architecture Overview

```
Controller (routers/)         — FastAPI route handlers, request/response schemas
      │  depends on (via Depends())
Service (services/)           — business logic, orchestrates repositories
      │  depends on (constructor injection)
Repository (repositories/)    — data access, one per model, extends BaseRepository
      │  depends on (constructor injection)
Model (models/)                — SQLAlchemy ORM entities
```

Services and Repositories are plain Python classes with no FastAPI imports — they
receive their dependencies via `__init__`, so they can be instantiated directly in
unit tests without any HTTP layer or DI framework involved. `Depends()` is only used
at the Controller layer, as the composition root that wires
`get_db_session → get_item_repository → get_item_service → route handler`.

Pydantic (`pydantic.BaseModel`, already a FastAPI dependency) is the validation layer
at the Controller boundary: request/response `schemas/` are Pydantic models, distinct
from the SQLAlchemy `models/` — routes never return ORM objects directly.

## Directory Structure

```
app/
  config.py                 # existing Settings, extended with DB/JWT env vars
  database.py                # async engine, session factory, declarative Base
  models/
    base.py                    # Base + TimestampMixin (created_at/updated_at)
    user.py                    # User
    item.py                    # Item
  schemas/
    user.py                    # UserCreate, UserRead
    item.py                    # ItemCreate, ItemUpdate, ItemRead
    auth.py                    # Token, TokenPayload
  repositories/
    base.py                    # BaseRepository[ModelType] — generic CRUD
    user_repository.py         # UserRepository(BaseRepository[User])
    item_repository.py         # ItemRepository(BaseRepository[Item])
  services/
    auth_service.py            # register/login, issues JWTs
    item_service.py            # business logic for items
  routers/
    auth.py                    # POST /auth/register, /auth/login (public)
    items.py                   # GET public; POST/PATCH/DELETE private
    health.py                  # GET /health (public)
  core/
    security.py                # password hashing (bcrypt), JWT encode/decode
    auth.py                     # enforce_auth dependency + @public decorator
    dependencies.py             # Depends() providers (get_db_session, get_item_repository, ...)
alembic/
  env.py, versions/
alembic.ini
tests/
  unit/
    services/
      test_item_service.py     # ItemService(fake_repo) — no DB, no HTTP
  integration/
    routers/
      test_items.py             # TestClient + real Postgres test DB
      test_auth.py
  conftest.py
```

## Data Layer

- `app/models/base.py` defines `Base` (SQLAlchemy `DeclarativeBase`) and a
  `TimestampMixin` (`created_at`, `updated_at`) that `User` and `Item` both inherit.
- `app/database.py` creates the async engine (`create_async_engine`, asyncpg driver)
  and an `async_sessionmaker` from `settings.database_url`.
- `BaseRepository[ModelType]` (generic over the ORM model) implements `get_by_id`,
  `list`, `create`, `update`, `delete` against an injected `AsyncSession`.
  `UserRepository` and `ItemRepository` extend it with entity-specific queries (e.g.
  `UserRepository.get_by_email`).

## Authentication

- **JWT bearer tokens.** `POST /auth/register` and `POST /auth/login` (both public)
  issue an access token; `core/security.py` handles password hashing (`bcrypt`
  package directly — not `passlib`, which has known incompatibilities with modern
  bcrypt) and JWT encode/decode (`pyjwt`).
- **Global, private-by-default enforcement.** All feature routers are included into
  one parent `api_router = APIRouter(dependencies=[Depends(enforce_auth)])`, mounted
  once in `main.py`. `/docs` and `/openapi.json` are registered directly on `app` and
  are unaffected.
- `enforce_auth` (in `core/auth.py`) inspects the matched route's endpoint function
  for an `__is_public__` marker. Absent → requires a valid bearer token, raises 401
  otherwise. Present → skips auth.
- A `@public` decorator sets that marker (`func.__is_public__ = True`). Any new route
  is private the instant it's added; making it public requires the explicit, visible
  `@public` decorator on the route itself — there is no separate "remember to wire up
  auth" step to forget.

## Dependency Injection

FastAPI's native `Depends()`, no container library:

```python
async def get_db_session() -> AsyncIterator[AsyncSession]: ...
def get_item_repository(session: AsyncSession = Depends(get_db_session)) -> ItemRepository: ...
def get_item_service(repo: ItemRepository = Depends(get_item_repository)) -> ItemService: ...
```

Routes depend only on `get_item_service`. Nothing in `services/` or `repositories/`
imports `fastapi`. Integration tests override `get_db_session` via
`app.dependency_overrides`; unit tests bypass `Depends()` entirely by constructing
`ItemService(fake_repository)` directly.

## Migrations

- Alembic configured for the async engine; `alembic/env.py` imports `Base.metadata`
  (with all model modules imported so autogenerate can see them) as
  `target_metadata`.
- Workflow: `docker compose exec api alembic revision --autogenerate -m "..."` then
  `docker compose exec api alembic upgrade head`.
- The dev container's entrypoint runs `alembic upgrade head` before starting
  `uvicorn`, so schema is always current on `docker compose up`.

## Testing Strategy

- **Unit tests** (`tests/unit/`): hand-written fake repository implementing the same
  interface as the real one, passed directly into a `Service`. No DB, no HTTP, no
  FastAPI involvement — fast and fully isolated.
- **Integration tests** (`tests/integration/`): `TestClient` against the real app,
  backed by a real Postgres **test** database (separate database name, same
  container as the app DB — see Docker Compose below). `conftest.py` provides:
  - a session-scoped fixture that creates tables against the test DB,
  - a per-test fixture that opens a transaction and rolls it back afterward (test
    isolation without recreating schema per test),
  - a `client` fixture applying `app.dependency_overrides[get_db_session]` to the
    transactional session,
  - an `auth_headers` fixture that registers/logs in a test user and returns a valid
    `Authorization: Bearer <token>` header for exercising private routes.

## Docker Compose Changes

- New `db` service: `postgres:16-alpine`, named volume for persistence, `pg_isready`
  healthcheck. `api` gets `depends_on: db: condition: service_healthy`.
- One Postgres container hosts **two databases** (app + test), created via an init
  script mounted into `/docker-entrypoint-initdb.d/` — avoids a second Postgres
  container just for tests.
- New env vars (`.env.example`): `DATABASE_URL`, `TEST_DATABASE_URL`,
  `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET_KEY`,
  `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`.
- New `requirements.txt` deps: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pyjwt`,
  `bcrypt`.

## Example Vertical Slices

- **User / Auth**: `User` model → `UserRepository` → `AuthService` (register, login,
  password verification, token issuance) → `routers/auth.py`
  (`POST /auth/register`, `POST /auth/login`, both `@public`).
- **Item**: `Item` model (id, name, description, owner_id, timestamps) →
  `ItemRepository` → `ItemService` → `routers/items.py`
  (`GET /items`, `GET /items/{id}` marked `@public`; `POST /items`,
  `PATCH /items/{id}`, `DELETE /items/{id}` private, require the current user via
  `enforce_auth`).

This pair is the template to copy when adding new resources: Model → Repository →
Service → Controller, mirrored by a unit test for the Service and an integration
test for the Controller.
