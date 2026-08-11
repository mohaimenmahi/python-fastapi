# python-fastapi

A FastAPI application.

## Project layout

```
main.py                  # FastAPI app instance, includes routers
app/
  config.py               # Settings (pydantic-settings, reads .env)
  routers/
    health.py              # GET /health
tests/
  test_health.py           # TestClient-based tests
requirements.txt
Dockerfile
docker-compose.yml
```

## Running the app

This project runs entirely through Docker — there's no local virtualenv. You need Docker running (e.g. OrbStack or Docker Desktop).

The Dockerfile has `development` and `production` build stages; `docker-compose.yml` picks one via the `ENVIRONMENT` variable in `.env` (defaults to `development`, which runs `uvicorn --reload`).

```bash
cp .env.example .env
docker compose up --build        # build the image and start the container, logs in foreground
docker compose up -d --build     # same, but detached (runs in the background)
```

The app is available at http://localhost:8000, with interactive docs at http://localhost:8000/docs. The project directory is mounted into the container, so local edits are picked up automatically by `--reload`.

Other useful commands while it's running:

```bash
docker compose logs -f api   # follow logs (only needed if started with -d)
docker compose ps            # list running services
docker compose down          # stop and remove the container
```

To run the `production` stage locally instead, set `ENVIRONMENT=production` in `.env` before running `docker compose up --build` (this drops `--reload` and runs the image the way it would run in production).

## Running tests

```bash
docker compose exec api pytest
```

Use `docker compose run --rm api pytest` instead if the container isn't already running.

## Building the production image directly

```bash
docker build --target production -t python-fastapi .
docker run -p 8000:8000 --env-file .env python-fastapi
```
