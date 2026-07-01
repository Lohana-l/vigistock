# ----------------------------------------------------------------------------
# Image commune : Dagster (webserver + daemon), simulateur, consumer, db-init,
# indexeur RAG. Exécution sans privilèges : tout tourne sous l'utilisateur
# applicatif `app` (uid 1000), jamais root.
#
# Note migration : si un volume dagster-home a été créé par une ancienne image
# (propriété root), le recréer une fois : `docker compose down` puis
# `docker volume rm vigistock_dagster-home` (ou `make nuke`).
# ----------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DAGSTER_HOME=/opt/dagster/dagster_home

# Utilisateur non privilégié : possède le code et le DAGSTER_HOME, de sorte
# que le volume nommé hérite de la bonne propriété à sa création.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p ${DAGSTER_HOME} \
    && chown -R app:app /app /opt/dagster
USER app
ENV HOME=/home/app

EXPOSE 3000
