#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f backend/docker-compose.yml up -d --build
curl --fail http://127.0.0.1:8000/health
