FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps (safe set for psycopg/psycopg2 builds if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# install deps first (better cache)
COPY requirements/ ./requirements/
RUN python -m pip install --no-cache-dir -U pip \
  && python -m pip install --no-cache-dir -r requirements/base.txt

# copy app code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
