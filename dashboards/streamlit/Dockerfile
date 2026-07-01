# syntax=docker/dockerfile:1.7
# ----------------------------------------------------------------------------
# Streamlit image: pharmacist-facing UI.
# Multipage app under dashboards/streamlit/, design system in lib/.
# ----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# curl is used by the docker-compose healthcheck.
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exécution sans privilèges : l'UI n'a aucune raison de tourner root.
# HOME est posé explicitement pour que Streamlit écrive ses caches
# (~/.streamlit) dans un répertoire qui appartient à l'utilisateur.
RUN useradd --create-home --uid 1000 app \
    && chown -R app:app /app
USER app
ENV HOME=/home/app

EXPOSE 8501

# Streamlit runs the multipage entry point. The native theme lives at
# dashboards/streamlit/.streamlit/config.toml - Streamlit picks it up
# automatically because we cd into that directory at startup.
WORKDIR /app/dashboards/streamlit

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
