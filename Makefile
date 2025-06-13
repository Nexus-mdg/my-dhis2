# Makefile for DHIS2 Docker Environment

# Variables
COMPOSE_FILE = docker-compose.yaml
SWARM_FILE = docker-compose.swarm.yaml
STACK_NAME = dhis2

# Docker Compose Commands
.PHONY: compose-up compose-down compose-restart compose-rebuild

compose-up:
	docker compose -f $(COMPOSE_FILE) up -d

compose-down:
	docker compose -f $(COMPOSE_FILE) down

compose-restart:
	docker compose -f $(COMPOSE_FILE) restart

compose-rebuild:
	docker compose -f $(COMPOSE_FILE) build
	docker compose -f $(COMPOSE_FILE) up -d

# Docker Swarm Commands
.PHONY: swarm-deploy swarm-redeploy swarm-remove swarm-update swarm-rebuild swarm-init-secrets

swarm-init-secrets:
	@echo "Creating Docker Swarm secrets from files in ./secrets directory..."
	@if [ -f ./secrets/postgres-user ]; then \
		docker secret create postgres-user ./secrets/postgres-user; \
	else \
		echo "Error: ./secrets/postgres-user not found"; \
		exit 1; \
	fi
	@if [ -f ./secrets/postgres-password ]; then \
		docker secret create postgres-password ./secrets/postgres-password; \
	else \
		echo "Error: ./secrets/postgres-password not found"; \
		exit 1; \
	fi
	@if [ -f ./secrets/postgres-db ]; then \
		docker secret create postgres-db ./secrets/postgres-db; \
	else \
		echo "Error: ./secrets/postgres-db not found"; \
		exit 1; \
	fi
	@if [ -f ./secrets/credentials ]; then \
		docker secret create credentials ./secrets/credentials; \
	else \
		echo "Error: ./secrets/credentials not found"; \
		exit 1; \
	fi
	@echo "All secrets created successfully"

swarm-deploy: swarm-init-secrets
	docker compose -f $(SWARM_FILE) build
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

swarm-redeploy:
	docker compose -f $(SWARM_FILE) build
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

swarm-remove:
	docker stack rm $(STACK_NAME)
	@echo "Removing Docker Swarm secrets..."
	docker secret rm postgres-user postgres-password postgres-db credentials || true

swarm-update:
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

swarm-rebuild:
	docker compose -f $(SWARM_FILE) build
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

# Volume Management
.PHONY: volume-list volume-prune

volume-list:
	docker volume ls | grep $(STACK_NAME)

volume-prune:
	@echo "WARNING: This will remove all unused volumes. Are you sure? [y/N]"
	@read -r response; \
	if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
		docker volume prune -f; \
	else \
		echo "Operation cancelled"; \
	fi

# Cleanup
.PHONY: clean

clean: swarm-remove
	@echo "Removing secret files in root directory..."
	rm -f postgres-user postgres-password postgres-db credentials
	@echo "Cleanup complete"

# Help
.PHONY: help

help:
	@echo "DHIS2 Docker Environment Management"
	@echo ""
	@echo "Docker Compose Commands:"
	@echo "  make compose-up        - Start all services using Docker Compose"
	@echo "  make compose-down      - Stop all services"
	@echo "  make compose-restart   - Restart all services"
	@echo "  make compose-rebuild   - Rebuild and restart all services"
	@echo ""
	@echo "Docker Swarm Commands:"
	@echo "  make swarm-init-secrets - Create Docker Swarm secrets from files in ./secrets directory"
	@echo "  make swarm-deploy      - Deploy the stack to Docker Swarm (includes creating secrets)"
	@echo "  make swarm-redeploy    - Deploy the stack to Docker Swarm (without creating secrets)"
	@echo "  make swarm-remove      - Remove the stack from Docker Swarm and remove secrets"
	@echo "  make swarm-update      - Update the stack in Docker Swarm"
	@echo "  make swarm-rebuild     - Rebuild images and update the stack"
	@echo ""
	@echo "Volume Management:"
	@echo "  make volume-list       - List all volumes used by the stack"
	@echo "  make volume-prune      - Remove all unused volumes (with confirmation)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Remove the stack, secrets, and secret files in root directory"
	@echo ""
	@echo "Help:"
	@echo "  make help              - Show this help message"
