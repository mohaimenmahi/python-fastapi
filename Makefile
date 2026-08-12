.PHONY: up upd down test migrate makemigrations logs shell

up:
	docker compose up --build

upd:
	docker compose up -d --build

down:
	docker compose down

test:
	docker compose exec api pytest

migrate:
	docker compose exec api alembic upgrade head

makemigrations:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

logs:
	docker compose logs -f api

shell:
	docker compose exec api bash
