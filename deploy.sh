#!/bin/bash
set -e

BRANCH="${1:-main}"   # usage: ./deploy.sh [branch]   (default: main)
COMPOSE_FILE="docker-compose.prod.yml"

echo "==> Pulling latest code from $BRANCH..."
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> Removing any old app containers (created outside compose, or by another project dir)..."
docker rm -f idea-atlas-backend idea-atlas-worker idea-atlas-frontend 2>/dev/null || true

echo "==> Building and starting idea-atlas..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Deployment complete. Running containers:"
docker ps --filter "name=idea-atlas"

echo "==> Recent backend logs:"
docker logs --tail 30 idea-atlas-backend

echo "==> Recent worker logs:"
docker logs --tail 30 idea-atlas-worker

echo "==> Readiness (DB + pgvector):"
sleep 5
docker exec idea-atlas-backend python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health/ready', timeout=10); print(r.read().decode())" || echo "readiness check failed — see backend logs"

echo "==> Recent frontend logs:"
docker logs --tail 30 idea-atlas-frontend
