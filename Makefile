.PHONY: docs-dev docs-build docs-clean

docs-dev: ## Start docs dev server with live reload
	uv run mkdocs serve --dirty

docs-build: ## Build docs site
	uv run mkdocs build

docs-clean: ## Remove built docs
	rm -rf site/
