#!/bin/bash

# Stop and remove existing container if it exists
docker stop code-sandbox 2>/dev/null || true
docker rm code-sandbox 2>/dev/null || true

# Build the Docker image
echo "Building code sandbox service..."
docker build -t code-sandbox .

# Run the container
echo "Starting code sandbox service on port 8856..."
docker run -d \
  --name code-sandbox \
  -p 8856:8856 \
  -v $(pwd)/datasets:/app/datasets:ro \
  --restart unless-stopped \
  code-sandbox

echo "Code sandbox service started!"
echo "Health check: curl http://localhost:8856/health" 