# DHIS2 Docker Swarm Environment Management

This repository provides a Makefile to simplify the management of the DHIS2 Docker Swarm environment. The Makefile includes commands for Docker Swarm operations, as well as volume management and cleanup.

For detailed information about the DHIS2 Docker Swarm environment itself, please refer to [SWARM.md](SWARM.md).

> **Disclaimer:** This codebase is intended for testing and demonstration purposes only. It is not designed or reviewed for production use. Use at your own risk.

## Prerequisites

- Docker installed on your system
- Docker Swarm initialized on your system

## Environment Files

The application requires environment files to run properly:

- **`.env.swarm`**: Contains environment variables for the Docker Swarm setup
  - Copy from `.env.swarm.example`: `cp .env.swarm.example .env.swarm`
  - Database credentials are loaded from secrets, not from this file

This file is mandatory for the application to run properly and is ignored by git to prevent committing sensitive information.

## Available Commands

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

If you encounter issues with the Docker Swarm commands, check the following:

1. Ensure Docker is properly installed
2. Ensure Docker Swarm is initialized
3. Check that all required secret files exist in the `./secrets` directory
4. Verify that you have created the required environment file:
   - `.env.swarm` for Docker Swarm mode
5. Review the logs for any error messages

For more detailed information about the DHIS2 Docker Swarm environment, including configuration and upgrading components, please refer to [SWARM.md](SWARM.md).
