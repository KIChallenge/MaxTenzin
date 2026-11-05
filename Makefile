# SV KI-Lotse — all commands run from repo root.  `make help` lists targets.
API := services/api
WEB := apps/web
UV  := uv run --project $(CURDIR)/$(API)

.PHONY: help setup dev api web seed test test-api test-extract eval lint extract openapi reset smoke-llm

help:             ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'

setup:            ## install backend + frontend deps
	cd $(API) && uv sync
	cd $(WEB) && npm install

dev:              ## run API (:8000) + web (:3000) together
	$(MAKE) -j2 api web

api:              ## FastAPI with reload, OpenAPI at http://localhost:8000/docs
	cd $(API) && uv run uvicorn app.main:app --reload --port 8000

web:              ## Next.js cockpit at http://localhost:3000
	cd $(WEB) && npm run dev

test: test-extract test-api   ## all tests (no docs/ and no LLM key needed)

test-api:         ## backend unit + smoke tests (LLM in fake mode)
	cd $(API) && LLM_MODE=fake uv run pytest -q app

test-extract:     ## validate committed extracted knowledge
	$(UV) pytest -q tools/extract

eval:             ## scenario + boundary evals (needs LLM key for live mode)
	cd $(API) && uv run pytest -q ../../evals

lint:             ## ruff
	cd $(API) && uv run ruff check app ../../tools

extract:          ## docs/ (raw, gitignored) -> knowledge/extracted/ (deterministic)
	cd tools/extract && $(UV) python run_all.py

openapi:          ## export OpenAPI spec + TS types for the web app
	cd $(API) && LLM_MODE=fake uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > $(CURDIR)/$(WEB)/lib/openapi.json
	cd $(WEB) && npx --yes openapi-typescript@7.4.4 lib/openapi.json -o lib/api-types.ts

seed:             ## load demo documents (from docs/) + import Stefan's e-Impfpass into the local DB
	cd $(API) && RAW_DATA_DIR=$(CURDIR)/docs uv run python -m app.services.documents.seed_demo

reset:            ## wipe local DB (var/)
	rm -rf var/*.db

smoke-llm:        ## check the Azure LLM connection from .env
	cd $(API) && uv run python -m app.core.llm
