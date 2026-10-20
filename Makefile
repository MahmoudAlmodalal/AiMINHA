PYTHON ?= python3
VENV := .venv/bin
COMPOSE := docker compose --env-file .env -f infra/compose.yaml

.PHONY: env setup db-up db-stop dev api web migrate migrations-check worker-check lint typecheck test unit contracts contracts-check build smoke smoke-identity smoke-catalog smoke-eligibility smoke-credits smoke-documents smoke-applications credits-timeouts ai-timeouts files-recover deadline-reminders secrets smoke-liveness check

env:
	$(PYTHON) scripts/setup.py

setup: env
	$(PYTHON) -m venv .venv
	$(VENV)/python -m pip install -r apps/api/requirements.txt
	npm ci --ignore-scripts --no-audit --no-fund

db-up:
	$(COMPOSE) up -d --wait

db-stop:
	$(COMPOSE) stop

dev:
	$(VENV)/python scripts/dev.py

api:
	$(VENV)/python apps/api/manage.py runserver 127.0.0.1:8000 --nothreading

web:
	npm run dev

migrate:
	$(VENV)/python apps/api/manage.py migrate --noinput

migrations-check:
	$(VENV)/python apps/api/manage.py makemigrations --check --dry-run
	$(VENV)/python apps/api/manage.py migrate --check

worker-check:
	$(VENV)/python apps/api/manage.py worker --check

lint:
	$(VENV)/ruff check apps/api scripts tests
	$(VENV)/ruff format --check apps/api scripts tests
	npm run lint

typecheck:
	$(VENV)/mypy
	npm run typecheck

test:
	$(VENV)/pytest
	npm test

unit:
	$(VENV)/pytest -m 'not django_db'
	npm test

contracts:
	$(VENV)/python scripts/contracts.py

contracts-check:
	$(VENV)/python scripts/contracts.py --check

build:
	npm run build

smoke:
	$(VENV)/python scripts/smoke.py

smoke-identity:
	$(VENV)/python scripts/smoke_identity.py

smoke-catalog:
	$(VENV)/python scripts/smoke_catalog.py

smoke-eligibility:
	$(VENV)/python scripts/smoke_eligibility.py

smoke-credits:
	$(VENV)/python scripts/smoke_credits.py

smoke-documents:
	$(VENV)/python scripts/smoke_documents.py

smoke-applications:
	$(VENV)/python scripts/smoke_applications.py

smoke-support:
	$(VENV)/python scripts/smoke_support.py

credits-timeouts:
	$(VENV)/python apps/api/manage.py mark_credit_timeouts

ai-timeouts:
	$(VENV)/python apps/api/manage.py mark_ai_timeouts

files-recover:
	$(VENV)/python apps/api/manage.py recover_private_files

deadline-reminders:
	$(VENV)/python apps/api/manage.py process_deadline_reminders

smoke-liveness:
	$(VENV)/python scripts/smoke.py --liveness-only

secrets:
	$(PYTHON) scripts/check_secrets.py

check: lint typecheck test contracts-check migrations-check secrets
	$(VENV)/python apps/api/manage.py check --fail-level WARNING
