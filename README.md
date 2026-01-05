# Commercial VPN Backend

Backend API for Commercial VPN service.

## Tech stack
- Python 3.12
- FastAPI
- SQLAlchemy + Alembic
- PostgreSQL
- Pytest

## Setup (local)

```bash
sudo apt install -y python3.12 python3.12-venv python3-pip
git clone https://github.com/sniffy137-creator/Commercial-vpn.git
cd Commercial-vpn/backend

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements/base.txt
pip install -r requirements/dev.txt

pytest
