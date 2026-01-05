# Commercial VPN — Backend (FastAPI)

Backend API for Commercial VPN.

## Requirements (local dev)
- Python 3.12+
- `uv` (optional but recommended)
- Docker + Docker Compose (for running Postgres)

---

## Quick start (Docker Compose)

### 1) Prepare env
Create `.env` file in `backend/` (next to `docker-compose.yml`):

Example (`backend/.env`):
```env
APP_NAME="Commercial VPN API"
ENV=local

DATABASE_URL="postgresql+psycopg2://commercialvpn:commercialvpn@db:5432/commercialvpn"

JWT_SECRET=dev-secret
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
