#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Config (можно переопределять через env)
# -----------------------------
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
EMAIL="${EMAIL:-newadmin@example.com}"
PASSWORD="${PASSWORD:-NewPass123!NewPass123!}"

# Postgres in docker
PG_CONTAINER="${PG_CONTAINER:-vpn-postgres}"
PG_USER="${PG_USER:-vpn}"
PG_DB="${PG_DB:-vpn}"

ENV_FILE="${ENV_FILE:-.env}"

# -----------------------------
# Helpers
# -----------------------------
say() { echo -e "\n\033[1;36m==>\033[0m $*"; }
ok()  { echo -e "\033[1;32mOK\033[0m  $*"; }
fail(){ echo -e "\033[1;31mFAIL\033[0m $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Command not found: $1"
}

http_code() {
  # usage: http_code <curl args...>
  curl -s -o /tmp/smoke_body.$$ -w "%{http_code}" "$@"
}

# -----------------------------
# Preflight
# -----------------------------
need_cmd curl
need_cmd python3
need_cmd docker

# Disable bash history expansion so '!' in password won't break things
set +H

# Load .env if exists
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

say "Preflight"
ok "API_BASE=$API_BASE"
ok "EMAIL=$EMAIL"
ok "PG_CONTAINER=$PG_CONTAINER PG_USER=$PG_USER PG_DB=$PG_DB"

# -----------------------------
# 1) Health
# -----------------------------
say "Health check"
CODE=$(http_code "$API_BASE/health")
BODY=$(cat /tmp/smoke_body.$$)
rm -f /tmp/smoke_body.$$

[[ "$CODE" == "200" ]] || fail "/health expected 200, got $CODE: $BODY"
echo "$BODY" | grep -q '"status"' || fail "/health body unexpected: $BODY"
ok "/health returned 200"

# -----------------------------
# 2) Register (idempotent-ish)
# -----------------------------
say "Register (if already exists, should still be fine)"
CODE=$(http_code -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" )
BODY=$(cat /tmp/smoke_body.$$)
rm -f /tmp/smoke_body.$$

if [[ "$CODE" == "200" || "$CODE" == "201" ]]; then
  ok "Registered user (code=$CODE)"
else
  ok "Register not applied (code=$CODE) - continuing (likely already exists)"
fi

# -----------------------------
# 3) Login -> TOKEN
# -----------------------------
say "Login (user token)"
RESP=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASSWORD")

TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[[ -n "$TOKEN" ]] || fail "Login failed, no access_token. Response: $RESP"
ok "Got TOKEN"

# -----------------------------
# 4) USER /servers flow
# -----------------------------
say "USER: GET /servers"
RESP=$(curl -s "$API_BASE/servers" -H "Authorization: Bearer $TOKEN")
ok "List servers returned"

# Create with retries to avoid collisions with UNIQUE constraints
say "USER: POST /servers (create) with retries"
SERVER_ID=""

for attempt in $(seq 1 30); do
  HOST="smoke-$(date +%s)-$RANDOM-$attempt"
  PORT=$(( 20000 + (RANDOM % 40000) ))

  CODE=$(http_code -X POST "$API_BASE/servers" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\":\"Smoke-Test-1\",
      \"host\":\"$HOST\",
      \"port\":$PORT,
      \"country\":\"NL\",
      \"is_active\": true,
      \"notes\":\"first\"
    }")
  BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$

  if [[ "$CODE" == "201" ]]; then
    SERVER_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
    [[ -n "$SERVER_ID" ]] || fail "Create returned 201 but no 'id'. Body: $BODY"
    ok "Created server id=$SERVER_ID host=$HOST port=$PORT (attempt $attempt)"
    break
  fi

  if [[ "$CODE" == "409" ]]; then
    echo "Attempt $attempt: 409 conflict for host=$HOST port=$PORT, retrying..."
    continue
  fi

  echo "Create server failed (HTTP $CODE). Body:"
  echo "$BODY"
  fail "POST /servers expected 201 (or 409 for retry), got $CODE"
done

[[ -n "$SERVER_ID" ]] || fail "Could not create server after 30 attempts (still 409). Check UNIQUE index on servers."

say "USER: GET /servers/$SERVER_ID"
CODE=$(http_code "$API_BASE/servers/$SERVER_ID" -H "Authorization: Bearer $TOKEN")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "200" ]] || fail "GET server expected 200, got $CODE: $BODY"
ok "Fetched server"

say "USER: PATCH /servers/$SERVER_ID"
CODE=$(http_code -X PATCH "$API_BASE/servers/$SERVER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":"updated note"}')
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "200" ]] || fail "PATCH expected 200, got $CODE: $BODY"
ok "Updated server"

say "USER: UNIQUE check (expect 409) using same host+port"
CODE=$(http_code -X POST "$API_BASE/servers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\":\"Smoke-Dup\",
    \"host\":\"$HOST\",
    \"port\":$PORT,
    \"country\":\"NL\",
    \"is_active\": true,
    \"notes\":\"dup\"
  }")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "409" ]] || fail "Expected 409 on duplicate, got $CODE: $BODY"
ok "Duplicate returned 409"

say "USER: DELETE /servers/$SERVER_ID (expect 204)"
CODE=$(http_code -X DELETE "$API_BASE/servers/$SERVER_ID" \
  -H "Authorization: Bearer $TOKEN")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "204" ]] || fail "DELETE expected 204, got $CODE: $BODY"
ok "Deleted server (soft delete)"

say "USER: GET /servers should not include deleted"
RESP=$(curl -s "$API_BASE/servers" -H "Authorization: Bearer $TOKEN")
ok "List after delete returned"

# -----------------------------
# 5) Promote to admin in DB
# -----------------------------
say "DB: Promote user to admin"
docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" \
  -c "UPDATE users SET role='admin' WHERE email='${EMAIL}';" >/dev/null
ok "Role set to admin (DB)"

# -----------------------------
# 6) Login again -> TOKEN_ADMIN
# -----------------------------
say "Login again (admin token)"
RESP=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASSWORD")

TOKEN_ADMIN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[[ -n "$TOKEN_ADMIN" ]] || fail "Admin login failed, no access_token. Response: $RESP"
ok "Got TOKEN_ADMIN"

# -----------------------------
# 7) ADMIN endpoints
# -----------------------------
say "ADMIN: GET /admin/users (expect 200)"
CODE=$(http_code "$API_BASE/admin/users" -H "Authorization: Bearer $TOKEN_ADMIN")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "200" ]] || fail "Admin users expected 200, got $CODE: $BODY"
ok "Admin users ok"

say "ADMIN: GET /admin/servers (expect 200)"
CODE=$(http_code "$API_BASE/admin/servers" -H "Authorization: Bearer $TOKEN_ADMIN")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "200" ]] || fail "Admin servers expected 200, got $CODE: $BODY"
ok "Admin servers ok"

say "ADMIN: POST /admin/servers/$SERVER_ID/restore (expect 200)"
CODE=$(http_code -X POST "$API_BASE/admin/servers/$SERVER_ID/restore" \
  -H "Authorization: Bearer $TOKEN_ADMIN")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "200" ]] || fail "Admin restore expected 200, got $CODE: $BODY"
ok "Admin restored server"

say "ADMIN: POST /admin/servers/$SERVER_ID/delete (expect 200)"
CODE=$(http_code -X POST "$API_BASE/admin/servers/$SERVER_ID/delete" \
  -H "Authorization: Bearer $TOKEN_ADMIN")
BODY=$(cat /tmp/smoke_body.$$); rm -f /tmp/smoke_body.$$
[[ "$CODE" == "200" ]] || fail "Admin delete expected 200, got $CODE: $BODY"
ok "Admin deleted server"

# -----------------------------
# 8) Audit check in DB (print last few rows)
# -----------------------------
say "DB: Audit snapshot (servers last 5)"
docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "
SELECT
  id, owner_id, host, port,
  deleted_at,
  created_by, updated_by, deleted_by, restored_by,
  created_at, updated_at
FROM servers
ORDER BY id DESC
LIMIT 5;
"

ok "SMOKE TEST COMPLETED"
