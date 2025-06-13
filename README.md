# DHIS2 Docker Environment Management

This repository provides a Makefile to simplify the management of the DHIS2 Docker environment. The Makefile includes commands for both Docker Compose and Docker Swarm operations, as well as volume management and cleanup.

For detailed information about the DHIS2 Docker environment itself, please refer to [DHIS2.md](DHIS2.md).

## Prerequisites

- Docker and Docker Compose installed on your system
- For Swarm mode: Docker Swarm initialized on your system

## Environment Files

The application requires environment files to run properly:

### For Docker Compose

- **`.env`**: Contains all environment variables for the Docker Compose setup
  - Copy from `.env.example`: `cp .env.example .env`
  - Contains database credentials and DHIS2 configuration

### For Docker Swarm

- **`.env.swarm`**: Contains environment variables for the Docker Swarm setup
  - Copy from `.env.swarm.example`: `cp .env.swarm.example .env.swarm`
  - Database credentials are loaded from secrets, not from this file

These files are mandatory for the application to run properly and are ignored by git to prevent committing sensitive information.

## Available Commands

### Docker Compose Commands

These commands manage the DHIS2 environment using Docker Compose:

- **Start the environment**:
  ```bash
  make compose-up
  ```

- **Stop the environment**:
  ```bash
  make compose-down
  ```

- **Restart all services**:
  ```bash
  make compose-restart
  ```

- **Rebuild and restart all services**:
  ```bash
  make compose-rebuild
  ```

### Docker Swarm Commands

These commands manage the DHIS2 environment using Docker Swarm:

- **Initialize Docker Swarm secrets**:
  ```bash
  make swarm-init-secrets
  ```
  This creates Docker Swarm secrets from files in the `./secrets` directory.

- **Deploy the stack to Docker Swarm**:
  ```bash
  make swarm-deploy
  ```
  This includes creating secrets and deploying the stack.

- **Remove the stack from Docker Swarm**:
  ```bash
  make swarm-remove
  ```
  This also removes the Docker Swarm secrets.

- **Update the stack in Docker Swarm**:
  ```bash
  make swarm-update
  ```

- **Rebuild images and update the stack**:
  ```bash
  make swarm-rebuild
  ```

### Volume Management

- **List all volumes used by the stack**:
  ```bash
  make volume-list
  ```

- **Remove all unused volumes**:
  ```bash
  make volume-prune
  ```
  This will prompt for confirmation before removing volumes.

### Cleanup

- **Remove the stack, secrets, and secret files in root directory**:
  ```bash
  make clean
  ```

### Help

- **Show help message with all available commands**:
  ```bash
  make help
  ```

## Secret Management

For Docker Swarm deployment, the following secrets are required in the `./secrets` directory:

- `postgres-user`: PostgreSQL username
- `postgres-password`: PostgreSQL password
- `postgres-db`: PostgreSQL database name
- `credentials`: DHIS2 credentials file (contains database username, password, and encryption password)

## Examples

### Starting with Docker Compose

```bash
# Start all services
make compose-up

# Check logs
docker logs dhis2

# Stop all services
make compose-down
```

### Deploying with Docker Swarm

```bash
# Initialize Docker Swarm (if not already done)
docker swarm init

# Deploy the stack
make swarm-deploy

# Check stack status
docker stack services dhis2

# Remove the stack
make swarm-remove
```

## Troubleshooting

If you encounter issues with the Docker Compose or Docker Swarm commands, check the following:

1. Ensure Docker and Docker Compose are properly installed
2. For Swarm mode, ensure Docker Swarm is initialized
3. Check that all required secret files exist in the `./secrets` directory
4. Verify that you have created the required environment files:
   - `.env` for Docker Compose mode
   - `.env.swarm` for Docker Swarm mode
5. Review the logs for any error messages

For more detailed information about the DHIS2 Docker environment, including configuration and upgrading components, please refer to [DHIS2.md](DHIS2.md).
