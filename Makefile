.PHONY: help
help:
	@echo "Usage:"
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'

DOCS=docs
DOCS_OUTPUT=$(DOCS)/_build
UV_DOCS_GROUPS="--group=docs"

PRETTIER=npm exec --package=prettier@3.6.0 -- prettier --print-width=99 --log-level warn # renovate: datasource=npm
PRETTIER_FILES="**/*.{yaml,yml,json,json5,css,md}"


.PHONY: lint
lint:
## lint: Lint the codebase with Prettier
	$(PRETTIER) --check $(PRETTIER_FILES)
	bash ${CURDIR}/.github/shellcheck-actions.sh

.PHONY: format
format:
## format: Formats both Markdown documents and YAML documents to preferred repository style.
	$(PRETTIER) --write $(PRETTIER_FILES)

.PHONY: setup
setup: setup-lint
## setup: Install the necessary tools for linting and testing.

.PHONY: setup-lint
setup-lint:
## setup-lint: Install the necessary tools for linting.
ifneq ($(shell which npx),)
else ifneq ($(shell which snap),)
	sudo snap install --classic --channel 22 node
else
	$(error Cannot find npx. Please install it on your system.)
endif
ifneq ($(shell which shellcheck),)
else ifneq ($(shell which snap),)
	sudo snap install shellcheck
else
	$(error Cannot find shellcheck. Please install it on your system.)
endif

.PHONY: setup-tests
setup-tests:
	echo "Installing nothing..."
	echo "Installed!"
ifdef SETUP_EXTRA
	echo "Setting up extra stuff"
endif

.PHONY: setup-docs
setup-docs: install-uv  ##- Set up a documentation-only environment
	uv sync --no-dev $(UV_DOCS_GROUPS)

.PHONY: clean
clean:  ## Clean up the development environment
	uv tool run pyclean .
	rm -rf dist/ build/ docs/_build/ docs/_linkcheck *.snap .coverage*

.PHONY: lint-docs
lint-docs:  ##- Lint the documentation
ifneq ($(CI),)
	@echo ::group::$@
endif
	uv run $(UV_DOCS_GROUPS) sphinx-lint \
	--ignore docs/_build --ignore docs/sphinx-docs-starter-pack \
	--enable all $(DOCS) -d missing-underscore-after-hyperlink,missing-space-in-hyperlink,line-too-long
	uv run $(UV_DOCS_GROUPS) sphinx-build -b linkcheck -W $(DOCS) docs/_linkcheck
ifneq ($(CI),)
	@echo ::endgroup::
endif

.PHONY: test-coverage
test-coverage:
	$(info Simulating coverage creation)
	$(info "Running tests with extra pytest options: ${PYTEST_ADDOPTS}")
	$(info "Markers set: $(MARKERS)")
	$(info "Using Python ${UV_PYTHON}")
	@touch coverage.xml

.PHONY: docs
docs:  ## Build documentation
	uv run $(UV_DOCS_GROUPS) sphinx-build -b dirhtml -W $(DOCS) $(DOCS_OUTPUT)

.PHONY: docs-auto
docs-auto:  ## Build and host docs with sphinx-autobuild
	uv run --group docs sphinx-autobuild -b dirhtml --open-browser --port=8080 --watch $(PROJECT) -W $(DOCS) $(DOCS_OUTPUT)

# Below are intermediate targets for setup. They are not included in help as they should
# not be used independently.

.PHONY: install-uv
install-uv:
ifneq ($(shell which uv),)
else ifneq ($(shell which snap),)
	sudo snap install --classic astral-uv
else ifneq ($(shell which brew),)
	brew install uv
else ifeq ($(OS),Windows_NT)
	pwsh -c "irm https://astral.sh/uv/install.ps1 | iex"
else
	curl -LsSf https://astral.sh/uv/install.sh | sh
endif
