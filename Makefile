# Makefile for DHIS2 Docker Environment

# Variables
SWARM_FILE = docker-compose.yaml
LOCAL_FILE = docker-compose.local.yml
STACK_NAME = dhis2
EXTERNAL_NETWORK = dhis2-external-net

# Download URLs and file names
TOMCAT_VERSION = 9.0.107
TOMCAT_URL = https://dlcdn.apache.org/tomcat/tomcat-9/v$(TOMCAT_VERSION)/bin/apache-tomcat-$(TOMCAT_VERSION).tar.gz
TOMCAT_FILE = shared/apache-tomcat-$(TOMCAT_VERSION).tar.gz

JDK_VERSION = 17.0.2
JDK_URL = https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_linux-x64_bin.tar.gz
JDK_FILE = shared/openjdk-$(JDK_VERSION)_linux-x64_bin.tar.gz

DHIS2_VERSION = 41.4.0
DHIS2_URL = https://releases.dhis2.org/41/dhis2-stable-$(DHIS2_VERSION).war
DHIS2_FILE = shared/dhis2.war

# Download Commands
.PHONY: shared download-tomcat download-jdk download-dhis2 download-all extract-tomcat extract-jdk setup-java setup-all

shared:
	@mkdir -p shared

download-tomcat: shared
	@echo "Downloading Tomcat $(TOMCAT_VERSION)..."
	wget --no-check-certificate -O $(TOMCAT_FILE) $(TOMCAT_URL)
	@echo "Downloaded Tomcat $(TOMCAT_VERSION) to shared directory"

download-jdk: shared
	@echo "Downloading OpenJDK $(JDK_VERSION)..."
	wget --no-check-certificate -O $(JDK_FILE) $(JDK_URL)
	@echo "Downloaded OpenJDK $(JDK_VERSION) to shared directory"

download-dhis2: shared
	@echo "Downloading DHIS2 $(DHIS2_VERSION)..."
	wget --no-check-certificate -O $(DHIS2_FILE) $(DHIS2_URL)
	@echo "Downloaded DHIS2 $(DHIS2_VERSION) as dhis2.war to shared directory"

download-all: download-tomcat download-jdk download-dhis2
	@echo "All downloads completed"

extract-tomcat: download-tomcat
	@echo "Extracting Tomcat $(TOMCAT_VERSION)..."
	@cd shared && tar -xzf apache-tomcat-$(TOMCAT_VERSION).tar.gz
	@echo "Tomcat extracted to shared/apache-tomcat-$(TOMCAT_VERSION)"

extract-jdk: download-jdk
	@echo "Extracting OpenJDK $(JDK_VERSION)..."
	@cd shared && tar -xzf openjdk-$(JDK_VERSION)_linux-x64_bin.tar.gz
	@echo "JDK extracted to shared/jdk-$(JDK_VERSION)"

setup-java: extract-tomcat extract-jdk
	@echo "Java environment setup completed"
	@echo "Tomcat location: shared/apache-tomcat-$(TOMCAT_VERSION)"
	@echo "JDK location: shared/jdk-$(JDK_VERSION)"

setup-all: setup-java download-dhis2
	@echo "Complete DHIS2 environment setup completed"
	@echo "Tomcat location: shared/apache-tomcat-$(TOMCAT_VERSION)"
	@echo "JDK location: shared/jdk-$(JDK_VERSION)"
	@echo "DHIS2 war file: shared/dhis2.war"

# Docker Swarm Commands
.PHONY: swarm-init deploy redeploy remove update rebuild init-secrets create-network

swarm-init:
	@echo "Initializing Docker Swarm..."
	@IP=$$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[^ ]+' | head -1); \
	if [ -z "$$IP" ]; then \
		IP=$$(hostname -I | awk '{print $$1}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$$'); \
	fi; \
	if [ -n "$$IP" ]; then \
		echo "Using IP address: $$IP"; \
		docker swarm init --advertise-addr $$IP || echo "Swarm already initialized or initialization failed"; \
	else \
		echo "Could not determine IP address. Please run manually: docker swarm init --advertise-addr <your-ip>"; \
		exit 1; \
	fi
	@echo "Docker Swarm initialization completed"

create-network:
	@echo "Creating external network $(EXTERNAL_NETWORK) if it does not exist yet..."
	@docker network inspect $(EXTERNAL_NETWORK) >/dev/null 2>&1 || \
		docker network create --driver overlay --attachable $(EXTERNAL_NETWORK) || \
		echo "Network creation attempt completed"
	@echo "External network check completed"

init-secrets:
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

deploy: init-secrets create-network
	@echo "Building images..."
	COMPOSE_IGNORE_ORPHANS=1 docker compose -f $(SWARM_FILE) build
	@echo "Waiting for swarm cluster to fully stop (5 seconds)..."
	@sleep 5
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

redeploy: remove volume-destroy
	@echo "Redeploying stack without creating secrets..."
	docker compose -f $(SWARM_FILE) build
	@echo "Waiting for swarm cluster to fully stop (5 seconds)..."
	@sleep 5
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME) || echo "Redeployment failed. Ensure the stack is removed first."
	@sleep 5
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME) || echo "Redeployment failed. Ensure the stack is removed first."

remove:
	docker stack rm $(STACK_NAME)
	@echo "Removing Docker Swarm secrets..."
	docker secret rm postgres-user postgres-password postgres-db credentials || true
	@echo "Waiting for stack to be removed (5 seconds)..."
	@sleep 5
	@echo "Removing external network if it exists..."
	@docker network inspect $(EXTERNAL_NETWORK) >/dev/null 2>&1 && \
		docker network rm $(EXTERNAL_NETWORK) || \
		echo "Network was already removed or doesn't exist"

update:
	@echo "Waiting for swarm cluster to fully stop (5 seconds)..."
	@sleep 5
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

rebuild:
	docker compose -f $(SWARM_FILE) build
	@echo "Waiting for swarm cluster to fully stop (5 seconds)..."
	@sleep 5
	docker stack deploy -c $(SWARM_FILE) $(STACK_NAME)

# Local Development Commands
.PHONY: up down sync-up sync-down

up:
	@echo "Starting local development environment..."
	docker compose -f $(LOCAL_FILE) up -d
	@echo "Local development environment started with docker-compose.local.yml"

down:
	@echo "Stopping local development environment..."
	docker compose -f $(LOCAL_FILE) down
	@echo "Local development environment stopped"

down-v:
	@echo "Stopping local development environment..."
	docker compose -f $(LOCAL_FILE) down -v
	@echo "Local development environment stopped"

sync-up:
	@echo "Starting sync services (db-sync and dhis2-sync)..."
	docker compose -f $(LOCAL_FILE) --profile sync up -d
	@echo "Sync services started with sync profile"

sync-down:
	@echo "Stopping sync services..."
	docker compose -f $(LOCAL_FILE) --profile sync down
	@echo "Sync services stopped"

sync-down-v:
	@echo "Stopping sync services..."
	docker compose -f $(LOCAL_FILE) --profile sync down -v
	@echo "Sync services stopped"

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

volume-destroy:
	docker volume rm -f dhis2_fileResource dhis2_logs dhis2_postgresql_data || echo "Volumes not found or already removed"

# Cleanup
.PHONY: clean

clean: remove
	@echo "Removing secret files in root directory..."
	rm -f postgres-user postgres-password postgres-db credentials
	@echo "Cleanup complete"

# Help
.PHONY: help

help:
	@echo "DHIS2 Docker Environment Management"
	@echo ""
	@echo "Local Development Commands:"
	@echo "  make up          - Start the local development environment with docker-compose.local.yml"
	@echo "  make down        - Stop the local development environment"
	@echo "  make sync-up     - Start the sync services (db-sync and dhis2-sync)"
	@echo "  make sync-down   - Stop the sync services"
	@echo ""
	@echo "Docker Swarm Commands:"
	@echo "  make init-secrets - Create Docker Swarm secrets from files in ./secrets directory"
	@echo "  make deploy      - Deploy the stack to Docker Swarm (includes creating secrets)"
	@echo "  make redeploy    - Deploy the stack to Docker Swarm (without creating secrets)"
	@echo "  make remove      - Remove the stack from Docker Swarm and remove secrets"
	@echo "  make update      - Update the stack in Docker Swarm"
	@echo "  make rebuild     - Rebuild images and update the stack"
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
