.PHONY: docs-dev docs-build docs-clean

docs-dev: ## Start docs dev server with live reload
	uv run mkdocs serve --dirty

docs-dev-remote: ## Start docs dev server accessible on LAN
	uv run mkdocs serve --dev-addr 0.0.0.0:$(or $(PORT),8989) --livereload

docs-build: ## Build docs site
	uv run mkdocs build

docs-clean: ## Remove built docs
	rm -rf site/
