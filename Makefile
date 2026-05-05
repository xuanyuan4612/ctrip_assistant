.PHONY: dev test build up down migrate clean fe-dev fe-build

dev:
	uv run uvicorn app.main:create_app --reload --host 0.0.0.0 --port 8000 --factory

install:
	uv sync

test:
	pytest tests/ -v --cov=app --cov-report=term

build:
	docker compose -f docker/docker-compose.yml build

up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down

migrate:
	alembic -c migrations/alembic.ini upgrade head

fe-dev:
	cd frontend && npm run dev

fe-build:
	cd frontend && npm run build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
