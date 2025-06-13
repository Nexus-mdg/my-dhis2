#!/bin/bash
set -e

# Create directory for SSL certificates
mkdir -p /etc/nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/nginx.key \
  -out /etc/nginx/ssl/nginx.crt \
  -subj "/C=MG/ST=Antananarivo/L=Antananarivo/O=DHIS2 Ingress/OU=IT/CN=dhis2.local"

# Set proper permissions
chmod 600 /etc/nginx/ssl/nginx.key
chmod 644 /etc/nginx/ssl/nginx.crt

echo "Self-signed SSL certificate generated successfully"