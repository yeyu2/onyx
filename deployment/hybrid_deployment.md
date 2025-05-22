# Onyx Hybrid Development Quick Start Guide

## Overview

This guide covers setting up Onyx in a hybrid development environment where infrastructure components run in Docker containers while frontend and backend code run locally for easy development.

## Architecture

- **Infrastructure (Docker)**: PostgreSQL, Redis, Vespa search, model servers, background workers
- **Development (Local)**: Backend API server, Frontend web application

## Quick Start

### 1. Start Infrastructure Services

```bash
# Navigate to docker compose directory
cd deployment/docker_compose

# Start essential infrastructure services
docker compose -f docker-compose.dev.yml -p onyx-stack up -d relational_db cache index inference_model_server indexing_model_server background
```

### 2. Set Up Local Backend

```bash
# Navigate to backend directory
cd ../../backend

# Install dependencies
pip install -r requirements/default.txt -r requirements/dev.txt

# Run backend server with auto-reload
python -m uvicorn onyx.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Set Up Local Frontend

```bash
# Navigate to web directory
cd ../../web

# Install dependencies
npm install

# Run frontend server
npm run dev
```

### 4. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8080

## Essential Services

| Service | Purpose | Port |
|---------|---------|------|
| relational_db | PostgreSQL database | 5432 |
| cache | Redis cache | 6379 |
| index | Vespa search engine | 8081, 19071 |
| inference_model_server | ML model serving | 9000 |
| indexing_model_server | ML model for indexing | 9001 |
| background | Task processing | - |

## Troubleshooting

### Files stuck in "scheduled" state
Problem: Uploaded documents never move past "scheduled" status
Solution: Ensure the `background` service is running:
```bash
docker compose -f docker-compose.dev.yml -p onyx-stack up -d background
```

### Model server connection errors
Problem: "Connection refused" errors for model server
Solution: Ensure the inference model server has port 9000 exposed:
```bash
# Check if properly exposed
docker ps | grep inference_model_server
```

### React hydration errors
Problem: Frontend shows hydration errors in development
Solution: This is a known issue with nested button elements in the UI. These errors don't appear in production builds.

## Checking Logs

```bash
# Backend logs
tail -f backend.log

# Docker service logs
docker logs onyx-stack-background-1
docker logs onyx-stack-inference_model_server-1
```

## Stopping Everything

```bash
# Stop Docker services
docker compose -f docker-compose.dev.yml -p onyx-stack down

# Stop local servers with Ctrl+C in their terminal windows
```

## Development Tips

1. Changes to backend code automatically reload when using `--reload` flag
2. Frontend changes are applied through Next.js hot reloading
3. Database changes require migrations to be run manually
4. When changing model configurations, restart the relevant model server

## Environment Configuration

Key environment variables are defined in `docker-compose.dev.yml`. For local development, you can create a `.env` file in the project root to override these values.

---

This hybrid approach makes development much faster by allowing you to modify and test code changes instantly while keeping infrastructure components stable.
