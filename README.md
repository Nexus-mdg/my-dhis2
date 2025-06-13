# DHIS2 Docker Environment

This repository contains a Docker-based environment for running DHIS2.

## Recent Updates

- **Tomcat Upgrade**: The environment has been upgraded from Tomcat 8.5.47 to Tomcat 9.0.78.

## Prerequisites

Before running the environment, you need to:

1. Download Apache Tomcat 9.0.78 from the official Apache Tomcat website:
   https://tomcat.apache.org/download-90.cgi

   Download the Core binary distribution (apache-tomcat-9.0.78.tar.gz) and place it in the `shared` directory.
   
   Direct download link:
   https://archive.apache.org/dist/tomcat/tomcat-9/v9.0.78/bin/apache-tomcat-9.0.78.tar.gz

2. Ensure you have Docker and Docker Compose installed on your system.

## Running the Environment

To start the environment, run:

```bash
docker-compose up -d
```

This will start the following services:
- DHIS2 application server (using Tomcat 9.0.78)
- PostgreSQL database
- Adminer (for database management)
- Sharer (for sharing files between containers)

## Configuration

The environment is configured through the following files:
- `docker-compose.yaml`: Defines the services and their relationships
- `Dockerfile`: Defines the DHIS2 container
- `entrypoint.sh`: Sets up the DHIS2 environment at runtime
- `tomcatconf-http/server.xml` and `tomcatconf-https/server.xml`: Tomcat configuration files

## Troubleshooting

If you encounter issues with the Tomcat upgrade, check the following:
1. Ensure you've downloaded the correct version of Tomcat (9.0.78) and placed it in the `shared` directory
2. Check the logs for any errors related to Tomcat startup
3. Verify that the DHIS2 WAR file is compatible with Tomcat 9