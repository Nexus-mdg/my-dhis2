FROM python:3.9-slim

WORKDIR /app

# Install curl (optional, for debugging or wait scripts)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint
CMD ["python", "app.py"]

