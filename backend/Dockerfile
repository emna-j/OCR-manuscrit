# Backend FastAPI — Secure Manuscript Intelligence Platform
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances d'abord (meilleur cache Docker).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif.
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Les fichiers uploadés restent hors de l'image en production (MinIO) ;
# ce volume couvre le mode "local" en développement.
VOLUME ["/app/data"]

EXPOSE 8000

# Applique les migrations puis démarre l'API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]