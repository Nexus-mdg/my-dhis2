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
- Ingress (for reverse proxy and file sharing)

## Configuration

The environment is configured through the following files:
- `docker-compose.yaml`: Defines the services and their relationships
- `Dockerfile`: Defines the DHIS2 container
- `entrypoint.sh`: Sets up the DHIS2 environment at runtime
- `tomcatconf-http/server.xml` and `tomcatconf-https/server.xml`: Tomcat configuration files

## Upgrading Components

### Upgrading JDK

The JDK version is configured using the `JAVA_ARCHIVE_FILE` environment variable in the `docker-compose.yaml` file. To upgrade the JDK:

1. Download the desired JDK version (e.g., JDK 17, 18, 19) as a tar.gz file.
2. Place the JDK tar.gz file in the `shared` directory.
3. Update the `JAVA_ARCHIVE_FILE` environment variable in `docker-compose.yaml`:

   ```yaml
   environment:
     JAVA_ARCHIVE_FILE: "jdk-18.tar.gz"  # Change to your new JDK file name
   ```

4. Restart the environment:

   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Upgrading Tomcat

Tomcat is configured in multiple places. To upgrade Tomcat:

1. Download the desired Tomcat version from the official Apache Tomcat website.
2. Place the Tomcat tar.gz file in the `shared` directory.
3. Update the following files:

   a. `Dockerfile`: Update the `CATALINA_HOME` environment variable:

   ```dockerfile
   ENV CATALINA_HOME="/opt/tomcat/apache-tomcat-9.0.106"  # Change to your new Tomcat version
   ```

   b. `entrypoint.sh`: Update the Tomcat download URL:

   ```bash
   wget -O /opt/tomcat/tomcat.tar.gz --no-check-certificate "https://ingress:8443/${TOMCAT_ARCHIVE_FILE}"  # Change to your new Tomcat version
   ```

   c. `download_tomcat9.sh`: Update the script to download the correct version:

   ```bash
   # Download Tomcat 9.0.106 and place it in the shared directory
   wget --no-check-certificate -O shared/apache-tomcat-9.0.106.tar.gz https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.106/bin/apache-tomcat-9.0.106.tar.gz
   echo "Downloaded Tomcat 9.0.106 to shared directory"
   ```

4. Restart the environment:

   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Upgrading PostgreSQL

PostgreSQL is configured in the `docker-compose.yaml` file. To upgrade PostgreSQL:

1. Update the PostgreSQL image version in `docker-compose.yaml`:

   ```yaml
   db:
     container_name: db
     image: postgis/postgis:13-3.1  # Change to your desired PostgreSQL version
   ```

2. If you're upgrading to a major version (e.g., from PostgreSQL 12 to 13), you'll need to handle the data migration:

   a. Backup your existing database:

   ```bash
   docker exec -t db pg_dumpall -c -U dhis > dump.sql
   ```

   b. Stop the environment and remove the PostgreSQL volume:

   ```bash
   docker-compose down
   docker volume rm my-dhis2_postgresql_data
   ```

   c. Start the environment with the new PostgreSQL version:

   ```bash
   docker-compose up -d
   ```

   d. Restore your database:

   ```bash
   cat dump.sql | docker exec -i db psql -U dhis
   ```

## Troubleshooting

If you encounter issues with the Tomcat upgrade, check the following:
1. Ensure you've downloaded the correct version of Tomcat and placed it in the `shared` directory
2. Check the logs for any errors related to Tomcat startup:

   ```bash
   docker logs dhis2
   ```

3. Verify that the DHIS2 WAR file is compatible with the Tomcat version you're using

If you encounter issues with the JDK upgrade:
1. Ensure the JDK tar.gz file is correctly named and placed in the `shared` directory
2. Check the logs for any Java-related errors:

   ```bash
   docker logs dhis2
   ```

If you encounter issues with the PostgreSQL upgrade:
1. Check the PostgreSQL logs:

   ```bash
   docker logs db
   ```

2. Ensure your backup and restore process was successful
3. If you're upgrading to a major version, check the PostgreSQL documentation for any breaking changes
