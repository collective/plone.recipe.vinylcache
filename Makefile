.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

.PHONY: release
release: ## Release to PyPI with zest.releaser (changelog, tag, upload, back to dev)
	uvx --from zest.releaser fullrelease

.PHONY: lint
lint: ## Run the same code analysis as CI
	tox -e lint

.PHONY: test
test: ## Run the tests (default: py312-plone62; override with ENV=...)
	tox -e $(or $(ENV),py312-plone62)
