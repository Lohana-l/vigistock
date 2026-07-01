# ----------------------------------------------------------------------------
# Vigistock: developer Makefile.
# `make help` lists every target; each target is documented inline so this
# file doubles as project documentation.
# ----------------------------------------------------------------------------

.DEFAULT_GOAL := help
SHELL := /bin/bash

PY ?= python3.11
PIP ?= pip

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[1;36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- Setup -------------------------------------------------------------
install: ## Install Python deps in the active virtualenv
	$(PIP) install -r requirements-dev.txt

env: ## Copy .env.example to .env if missing
	@test -f .env || cp .env.example .env

# --- Stack -------------------------------------------------------------
up: env ## Start the full local stack (Redpanda + Timescale + Grafana + Ollama + Streamlit + Dagster)
	docker compose up -d
	@echo ""
	@echo "  Streamlit  : http://localhost:8501"
	@echo "  Grafana    : http://localhost:3000  (admin/admin)"
	@echo "  Dagster    : http://localhost:3001"
	@echo "  Redpanda   : localhost:9092"
	@echo "  Timescale  : localhost:5432"

down: ## Stop the stack (keeps volumes)
	docker compose down

nuke: ## Stop the stack and DELETE all volumes (clean slate)
	docker compose down -v

logs: ## Tail the docker-compose logs
	docker compose logs -f --tail=100

# --- Pipeline ---------------------------------------------------------
schema: ## Apply TimescaleDB schema (hypertables, continuous aggregates)
	$(PY) scripts/apply_schema.py

seed: ## Seed reference data (sites, frigos, medicaments, lots, historique)
	$(PY) -m scripts.seed_dimensions

ingest: ## Run all batch ingestion jobs (FDA, openFDA, ANSM, OpenPrescribing)
	$(PY) -m ingestion.main --all

pull-models: ## Download the Ollama chat model (embeddings run locally via sentence-transformers)
	docker exec vigistock-ollama ollama pull $${OLLAMA_MODEL:-phi3:mini}

index-rag: ## Index protocol PDFs into ChromaDB
	$(PY) -m llm.indexer.run

simulate: ## Run cold-chain IoT simulator vers Redpanda
	$(PY) -m simulator.run

consume: ## Run streaming consumer (Redpanda vers TimescaleDB + anomaly detection)
	$(PY) -m streaming.consumer

forecast: ## Run Prophet shortage-prediction job
	$(PY) -m ml.shortage_forecast

pipeline: schema seed ingest forecast ## Run the full batch pipeline (schema + seed + ingest + forecast)

app: ## Run Streamlit locally (without docker)
	cd dashboards/streamlit && streamlit run app.py

# --- Quality / CI -----------------------------------------------------
lint: ## Lint Python + SQL
	ruff check .
	sqlfluff lint sql --dialect postgres

typecheck: ## Static typing (mypy, configure dans pyproject.toml)
	mypy . || true   # informatif : ne bloque pas tant que la dette de typage n'est pas resorbee

format: ## Auto-format code
	ruff format .

test: ## Run unit tests
	pytest -m "not integration and not llm" -q

coverage: ## Unit tests + rapport de couverture HTML (htmlcov/)
	pytest -m "not integration and not llm" -q \
		--cov=ingestion --cov=streaming --cov=simulator --cov=ml --cov=llm \
		--cov-report=term-missing --cov-report=html

audit: ## Securite : bandit (SAST) + pip-audit (dependances)
	bandit -r . -x ./tests,./notebooks --severity-level high
	pip-audit -r requirements.txt -r requirements-dev.txt || true

test-integration: ## Run integration tests (needs running stack)
	pytest -m integration -q

ci: lint test ## Run everything CI runs

clean: ## Remove caches and temp files
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ build dist *.egg-info


