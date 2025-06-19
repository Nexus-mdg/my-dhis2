FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create secrets directory with proper permissions
RUN mkdir -p /app/secrets && chmod 755 /app/secrets

# Copy and set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]