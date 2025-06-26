# DHIS2 Docker Swarm Deployment

This document provides instructions for deploying the DHIS2 application using Docker Swarm for orchestration.

## Prerequisites

Before deploying with Docker Swarm, ensure you have:

1. Docker Engine installed on all nodes (version 19.03.0+)
2. `wget` installed for downloading components
3. Sufficient resources on your nodes to meet the defined resource requirements
4. Network connectivity to download required components

## Quick Start

The deployment process has been streamlined with Makefile commands. Follow these steps:

### 1. Initialize Docker Swarm

```bash
make swarm-init
```

This will automatically:
- Detect the best IP address for your system
- Handle multiple network interfaces and IPv6 conflicts
- Initialize Docker Swarm with the appropriate settings

### 2. Download and Setup Components

```bash
make setup-all
```

This will automatically:
- Download Tomcat 9.0.106
- Download OpenJDK 17.0.2
- Download DHIS2 41.4.0 war file
- Extract Tomcat and JDK to the shared directory
- Rename the DHIS2 war file to `dhis2.war`

### 3. Deploy the Stack

```bash
make deploy
```

This will automatically:
- Create Docker Swarm secrets from files in the `./secrets` directory
- Create the external network if it doesn't exist
- Build the required images
- Deploy the complete DHIS2 stack

## Individual Commands

If you need more control, you can run individual commands:

### Download Components Separately
```bash
make download-tomcat    # Download Tomcat only
make download-jdk       # Download JDK only
make download-dhis2     # Download DHIS2 war file only
make download-all       # Download all components
```

### Setup Java Environment
```bash
make setup-java         # Extract Tomcat and JDK only
```

### Docker Swarm Management
```bash
make swarm-init         # Initialize Docker Swarm
make deploy             # Deploy the stack
make redeploy           # Redeploy (removes volumes)
make remove             # Remove the stack and secrets
make update             # Update the stack
make rebuild            # Rebuild images and update
```

## Checking Stack Status

To check the status of your deployed stack:

```bash
# List all stacks
docker stack ls

# List services in the dhis2 stack
docker stack services dhis2

# List tasks (containers) in the dhis2 stack
docker stack ps dhis2
```

## Managing the Deployment

### Scaling Services

To scale a specific service (e.g., increase the number of dhis2 instances):

```bash
docker service scale dhis2_dhis2=2
```

### Updating Services

To update the stack after making changes:

```bash
make update
```

### Stopping the Stack

To stop and remove the entire stack:

```bash
make remove
```

This will:
- Remove the Docker stack
- Remove Docker Swarm secrets
- Remove the external network
- Clean up resources

### Volume Management

```bash
make volume-list        # List volumes used by the stack
make volume-prune       # Remove unused volumes (with confirmation)
make volume-destroy     # Remove specific DHIS2 volumes
```

### Complete Cleanup

```bash
make clean
```

This will remove the stack, secrets, and secret files in the root directory.

## Component Versions

The following versions are automatically downloaded:

- **Tomcat**: 9.0.106
- **OpenJDK**: 17.0.2
- **DHIS2**: 41.4.0

## Directory Structure

After running `make setup-all`, your directory will contain:

```
shared/
├── apache-tomcat-9.0.106.tar.gz    # Downloaded Tomcat archive
├── apache-tomcat-9.0.106/          # Extracted Tomcat
├── openjdk-17.0.2_linux-x64_bin.tar.gz  # Downloaded JDK archive
├── jdk-17.0.2/                     # Extracted JDK
└── dhis2.war                       # DHIS2 application
```

## Troubleshooting

### Network Issues
If you encounter network conflicts, the Makefile handles this automatically by using `COMPOSE_IGNORE_ORPHANS=1`.

### Multiple IP Addresses
The `swarm-init` command automatically detects the best IP address and handles IPv6 conflicts.

### Help
For a complete list of available commands:

```bash
make help
```
