PROJECT=starflow
SOURCES=$(wildcard *.py) $(PROJECT) tests
DOCS=docs

ifneq ($(OS),Windows_NT)
	OS := $(shell uname)
endif

.DEFAULT_GOAL := help

.ONESHELL:

.SHELLFLAGS = -ec

.PHONY: help
help: ## Show this help.
	@printf "%-41s %s\n" "Target" "Description"
	@printf "%-41s %s\n" "------" "-----------"
	@fgrep " ##" $(MAKEFILE_LIST) | fgrep -v grep | sed 's/:[^#]*/ /' | awk -F '[: ]*' \
	'{
		if ($$2 == "##")
		{
			$$1=sprintf("%-40s", $$1);
			$$2="";
			print $$0;
		}
		else
		{
			$$1=sprintf(" └%-38s", $$1);
			$$2="";
			print $$0;
		}
	}'

---------------- : ## ----------------

.PHONY: setup
setup: install-uv setup-precommit ## Set up a development environment

.PHONY: setup-lint
setup-lint: install-npx  ##- Set up a linting environment

.PHONY: setup-docs
setup-docs: install-uv  ##- Set up a documentation-only environment
	uv sync --frozen --no-dev --no-install-workspace --extra docs

.PHONY: setup-precommit
setup-precommit: install-uv  ##- Set up pre-commit hooks in this repository.
ifeq ($(shell command -v pre-commit),)
	uv tool install pre-commit
endif
	pre-commit install

---------------- : ## ----------------

.PHONY: lint
lint: lint-prettier lint-shellcheck ## Run all linters

.PHONY: lint-prettier
lint-prettier: install-npx  ##- Lint with prettier
	npx prettier --print-width=99 --check .

lint-shellcheck:  ##- Lint actions with shellcheck.
	bash ${CURDIR}/.github/shellcheck-actions.sh

.PHONY: format
format: install-npx ## Format both Markdown documents and YAML documents to preferred repository style.
	npx prettier --print-width=99 --write .

.PHONY: install-npx
install-npx:
ifneq ($(shell command -v npx),)
else ifneq ($(shell command -v snap),)
	sudo snap install --classic node
else
	$(error Could not find npx. Please install node.)
endif

.PHONY: install-shellcheck
install-shellcheck:
ifneq ($(shell command -v shellcheck),)
else ifneq ($(shell command -v shellcheck),)
	sudo snap install shellcheck
else
	$(error Could not find shellcheck. Please install it manually.)
endif
