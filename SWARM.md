# DHIS2 Docker Swarm Deployment

This document provides instructions for deploying the DHIS2 application using Docker Swarm for orchestration.

## Prerequisites

Before deploying with Docker Swarm, ensure you have:

1. Docker Engine installed on all nodes (version 19.03.0+)
2. Docker Swarm initialized on the manager node
3. All required files in the shared directory (JDK, Tomcat, DHIS2 WAR)
4. Sufficient resources on your nodes to meet the defined resource requirements

## Initializing Docker Swarm

If you haven't already initialized a swarm, run the following on the manager node:

```bash
docker swarm init --advertise-addr <MANAGER-IP>
```

To add worker nodes to the swarm, run the command provided in the output of the above command on each worker node.

## Building and Deploying the Stack

### Building the Images

Before deploying the stack, build the required images:

```bash
# Build the images without starting containers
docker-compose -f docker-compose.swarm.yaml build
```

### Deploying the Stack

To deploy the entire stack to the swarm:

```bash
docker stack deploy -c docker-compose.swarm.yaml dhis2
```

This will create a stack named "dhis2" with all the services defined in the docker-compose.swarm.yaml file.

### Checking Stack Status

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

To update a service with a new image or configuration:

1. Make changes to the docker-compose.swarm.yaml file
2. Redeploy the stack:

```bash
docker stack deploy -c docker-compose.swarm.yaml dhis2
```

### Stopping the Stack

To stop and remove the entire stack:

```bash
docker stack rm dhis2
```

### Rebuilding Services

To rebuild and update a specific service:

1. Rebuild the image:

```bash
docker-compose -f docker-compose.swarm.yaml build <service-name>
```

2. Push the image to a registry if using multiple nodes:

```bash
docker-compose -f docker-compose.swarm.yaml push <service-name>
```

3. Force update the service:

```bash
docker service update --force dhis2_<service-name>
```

## Volume Management

### Listing Volumes

To list all volumes used by the stack:

```bash
docker volume ls | grep dhis2
```

### Backing Up Volumes

To back up the PostgreSQL data volume:

```bash
# Create a temporary container to access the volume
docker run --rm -v dhis2_postgresql_data:/source -v $(pwd):/backup ubuntu tar -czvf /backup/postgresql_backup.tar.gz -C /source .
```

### Pruning Volumes

To remove unused volumes (be careful as this will delete data):

```bash
# Remove all unused volumes
docker volume prune

# Remove specific volumes (after stack is removed)
docker volume rm dhis2_postgresql_data dhis2_fileResource dhis2_logs
```

## Resource Management

The docker-compose.swarm.yaml file defines resource limits for each service:

- **sharer**: 0.5 CPU, 256MB memory
- **db**: 1.0 CPU, 1GB memory
- **adminer**: 0.3 CPU, 128MB memory
- **dhis2**: 2.0 CPU, 4GB memory

To monitor resource usage:

```bash
docker stats $(docker ps --format={{.Names}})
```

## Troubleshooting

### Viewing Logs

To view logs for a specific service:

```bash
docker service logs dhis2_dhis2
```

### Checking Service Health

To check the health of services:

```bash
docker service ps dhis2_dhis2
```

### Common Issues

1. **Services not starting**: Check logs and ensure resource limits are not too restrictive
2. **Network connectivity issues**: Ensure overlay network is properly configured
3. **Volume mounting issues**: Check if volumes are properly created and accessible

## Security Considerations

### Managing Secrets

The stack uses Docker Secrets to securely manage sensitive information:

1. **Database Credentials**: PostgreSQL credentials are stored as Docker Secrets:
   - `postgres-user`: Database username
   - `postgres-password`: Database password
   - `postgres-db`: Database name

To create or update these secrets:

```bash
# Create secret files
echo "your_username" > postgres-user
echo "your_secure_password" > postgres-password
echo "your_database_name" > postgres-db

# Update the stack to use the new secrets
docker stack deploy -c docker-compose.swarm.yaml dhis2
```

To view the current secrets:

```bash
docker secret ls
```

To remove a secret (requires removing the stack first):

```bash
docker stack rm dhis2
docker secret rm postgres-user postgres-password postgres-db
```

### General Security Recommendations

1. Use Docker secrets for all sensitive information (credentials, certificates)
2. Implement network segmentation using overlay networks
3. Regularly update base images and dependencies
4. Implement proper access controls for the Docker daemon

## Get swarm IP

```bash
docker network inspect docker_gwbridge
```
