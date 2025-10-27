.PHONY: help build up down logs test clean restart backend-test frontend-test

ENV_FILE = .env
COMPOSE = docker-compose --env-file $(ENV_FILE)

help:
	@echo "  OpsCraft 					- Available Commands"
	@echo ""
	@echo "  make build          		- Build all Docker images"
	@echo "  make up             		- Start all services"
	@echo "  make down           		- Stop all services"
	@echo "  make restart        		- Restart all services"
	@echo "  make logs           		- View logs from all services"
	@echo "  make test           		- Run all tests"
	@echo "  make backend-test   		- Run backend tests"
	@echo "  make frontend-test  		- Run frontend tests"
	@echo "  make clean          		- Clean up containers and volumes"
	@echo "  make db-shell       		- Access PostgreSQL shell"
	@echo "  make backend-shell  		- Access backend container shell"
	@echo ""

build:
	$(COMPOSE) build --no-cache

up:
	$(COMPOSE) up -d
	@echo "Services started! Access the app at:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

logs-backend:
	$(COMPOSE) logs -f backend

logs-frontend:
	$(COMPOSE) logs -f frontend_dev

logs-celery:
	$(COMPOSE) logs -f celery_worker

test: backend-test frontend-test

backend-test:
	$(COMPOSE) exec backend pytest tests/ -v

backend-test-coverage:
	$(COMPOSE) exec backend pytest tests/ --cov=app --cov-report=html

frontend-test:
	$(COMPOSE) exec frontend_dev npm test -- --watchAll=false

frontend-test-coverage:
	$(COMPOSE) exec frontend_dev npm test -- --coverage --watchAll=false

clean:
	$(COMPOSE) down -v
	docker system prune -f

db-shell:
	$(COMPOSE) exec db psql -U devops -d ops_craft

backend-shell:
	$(COMPOSE) exec backend /bin/bash

redis-cli:
	$(COMPOSE) exec redis redis-cli

migrate:
	$(COMPOSE) exec backend alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$msg"

dev:
	$(COMPOSE) -f docker-compose.dev.yml up -d

dev-down:
	$(COMPOSE) -f docker-compose.dev.yml down