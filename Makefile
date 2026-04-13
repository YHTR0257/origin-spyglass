PREK ?= prek
DOCKER_COMPOSE ?= docker compose

.PHONY: uv-setup build up down logs test-backend

uv-setup:
	bash scripts/setup_uv.sh

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

test-backend:
	cd backend && uv run pytest
