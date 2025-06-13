FROM nginx:stable-alpine

# Install OpenSSL for certificate generation
RUN apk add --no-cache openssl bash

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy certificate generation script
COPY generate-certs.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/generate-certs.sh

# Create directory for SSL certificates
RUN mkdir -p /etc/nginx/ssl

# Generate self-signed certificates on container start
CMD ["/bin/bash", "-c", "/usr/local/bin/generate-certs.sh && nginx -g 'daemon off;'"]