#!/bin/bash
set -e

BRANCH="main"
COMPOSE_FILE="docker-compose.prod.yml"

echo "==> Pulling latest code from $BRANCH..."
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> Removing any old app containers (created outside compose, or by another project dir)..."
docker rm -f idea-atlas-backend idea-atlas-frontend 2>/dev/null || true

echo "==> Building and starting idea-atlas..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Deployment complete. Running containers:"
docker ps --filter "name=idea-atlas"

echo "==> Recent backend logs:"
docker logs --tail 30 idea-atlas-backend

echo "==> Recent frontend logs:"
docker logs --tail 30 idea-atlas-frontend
