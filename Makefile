API := services/api
UV  := uv run --project $(CURDIR)/$(API)

.PHONY: setup extract test-extract
setup:            ## install backend deps
	cd $(API) && uv sync
extract:          ## docs/ (raw) -> knowledge/extracted/ (deterministic)
	cd tools/extract && $(UV) python run_all.py
test-extract:     ## validate extracted knowledge (no docs/ needed)
	$(UV) pytest -q tools/extract
