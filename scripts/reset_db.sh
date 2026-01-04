#!/usr/bin/env bash
set -euo pipefail

# Reset Postgres volume + run Alembic migrations end-to-end (from backend/)
# Usage:
#   chmod +x scripts/reset_db.sh
#   ./scripts/reset_db.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> [1/7] Loading .env (if exists)"
set -a
if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source ".env"
else
  echo "WARN: .env not found in $ROOT_DIR"
fi
set +a

: "${DATABASE_URL:=}"
if [[ -z "${DATABASE_URL}" ]]; then
  echo "WARN: DATABASE_URL is empty (alembic will rely on app settings)"
else
  echo "OK  DATABASE_URL=${DATABASE_URL}"
fi

echo
echo "==> [2/7] Stopping stack and removing volumes"
docker compose down -v

echo
echo "==> [3/7] Starting Postgres"
docker compose up -d

echo
echo "==> [4/7] Waiting for Postgres to become healthy"
PG_CONTAINER="${PG_CONTAINER:-vpn-postgres}"

# wait up to ~60s
for i in {1..60}; do
  status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$PG_CONTAINER" 2>/dev/null || true)"
  if [[ "$status" == "healthy" ]]; then
    echo "OK  $PG_CONTAINER is healthy"
    break
  fi

  if [[ "$status" == "no-healthcheck" ]]; then
    echo "WARN: container has no healthcheck, trying psql probe..."
    break
  fi

  echo "  ... ($i/60) status=$status"
  sleep 1
done

echo
echo "==> [5/7] Running Alembic migrations"
# Important: alembic uses backend/alembic.ini and env.py
alembic upgrade head

echo
echo "==> [6/7] DB sanity checks"
PG_USER="${PG_USER:-vpn}"
PG_DB="${PG_DB:-vpn}"

docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -P pager=off -c "\dt"
docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -P pager=off -c "\d users" || true
docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -P pager=off -c "\d servers" || true
docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -P pager=off -c "\dT+ user_role" || true

echo
echo "==> [7/7] Done"
echo "Next:"
echo "  uvicorn app.main:app --reload"
echo "  ./scripts/smoke.sh"
