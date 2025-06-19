#!/bin/bash
set -e

echo "Starting DHIS2 root user creation process..."

# Read credentials from secret files
if [ -f /run/secrets/admin-credentials ]; then
    echo "Reading admin credentials from secret file..."
    export DHIS2_USERNAME=$(head -n 1 /run/secrets/admin-credentials)
    export DHIS2_PASSWORD=$(head -n 2 /run/secrets/admin-credentials | tail -n 1)
    echo "Using credentials from secret file"
else
    echo "Warning: Admin credentials secret file not found"
    exit 1
fi

# Set DHIS2 URL
export DHIS2_URL=${DHIS2_URL:-https://dhis2:8443}

echo "DHIS2 URL: $DHIS2_URL"
echo "Username: $DHIS2_USERNAME"

# Run the Python application to create root user
echo "Running root user creation script..."
python app.py

# Set permissions for output files
echo "Setting permissions for output files..."
chmod -R 777 /app/secrets/ 2>/dev/null || true

echo "Root user creation process completed successfully!"