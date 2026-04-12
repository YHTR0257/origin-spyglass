PREK ?= prek
DOCKER_COMPOSE ?= docker compose

.PHONY: uv-setup build up down logs

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
