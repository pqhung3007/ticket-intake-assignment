.DEFAULT_GOAL := help
COMPOSE := docker compose

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Start db + backend + frontend (hot reload) in the background
	$(COMPOSE) up --build -d
	@echo "Web UI:   http://localhost:$${WEB_PORT:-5173}"
	@echo "API docs: http://localhost:$${API_PORT:-8000}/api/v1/docs"

down: ## Stop the stack (data is kept)
	$(COMPOSE) down

logs: ## Follow logs of all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

prod: ## Run the production image locally on :8080
	$(COMPOSE) --profile prod up --build -d app
	@echo "Production image: http://localhost:$${PROD_PORT:-8080}"

psql: ## Open a psql shell in the database
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-tickets} -d $${POSTGRES_DB:-tickets}

migrate: ## Apply migrations (also done automatically on backend start)
	$(COMPOSE) exec backend alembic upgrade head

migration: ## Create a migration from model changes: make migration m="add x"
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

test: ## Run backend tests inside the backend container (uses a separate test database)
	$(COMPOSE) exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB -tc "select 1 from pg_database where datname = '"'"'tickets_test'"'"'" | grep -q 1 || createdb -U $$POSTGRES_USER tickets_test'
	$(COMPOSE) exec -e TEST_DATABASE_URL=postgresql://$${POSTGRES_USER:-tickets}:$${POSTGRES_PASSWORD:-tickets}@db:5432/tickets_test backend pytest -q

seed: ## Fill the running app with realistic demo tickets (safe to re-run)
	python3 backend/scripts/seed_demo.py http://localhost:$${API_PORT:-8000}

reset-db: ## DELETE all local data (drops the pgdata volume)
	$(COMPOSE) down -v

.PHONY: help up down logs ps prod psql migrate migration test seed reset-db
