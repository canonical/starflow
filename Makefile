# Env vars for the docs Starter Pack. They must be exported so make can pass them to the
# docs Makefile.
export DOCS_BUILDDIR ?= _build
export DOCS_VENVDIR ?= ../.venv
export VALEDIR ?= $(VENVDIR)/lib/python*/site-packages/vale

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
setup-docs: _setup-docs
## setup-docs: Set up the documentation environment
ifneq ($(CI),)
	@echo ::group::$@
endif
	uv sync --no-dev $(UV_DOCS_GROUPS)
ifneq ($(CI),)
	@echo ::endgroup::
endif

.PHONY: _setup-docs
_setup-docs: install-uv

.PHONY: clean
clean:
## clean: Clean up the development environment
	uv tool run pyclean .
	rm -rf dist/ build/ docs/_build/ docs/_linkcheck *.snap .coverage* .venv

# Alias for `html` target in docs project. We want to use our own `.venv`, so we
# replace it.
.PHONY: docs
docs: docs-install
## docs: Render the documentation to disk
ifneq ($(CI),)
	@echo ::group::$@
endif
	$(MAKE) -C docs html --no-print-directory
ifneq ($(CI),)
	@echo ::endgroup::
endif

# Alias for `serve` target in docs project
.PHONY: docs-auto
docs-auto: docs-install
##  docs-auto: Render the documentation in a live session
	$(MAKE) -C docs run --no-print-directory

# Override for `install` target in docs project. We still need the Vale setup, so we
# run that after the parent docs setup.
.PHONY: docs-install
docs-install: setup-docs
##  docs-install: Set up documentation packages
ifneq ($(CI),)
	@echo ::group::$@
endif
	$(MAKE) -C docs vale-install --no-print-directory
ifneq ($(CI),)
	@echo ::endgroup::
endif

# Alias for `setup-docs`
.PHONY: docs-setup
docs-setup: setup-docs

# Override for `clean` target in docs project. We don't want to touch `.venv`, so
# we pass a null dir instead.
.PHONY: docs-clean
docs-clean:
##  docs-clean: Clean the temporary files used in documentation
	VENVDIR=$(mktemp)
	$(MAKE) -C docs clean --no-print-directory

# Override for `help` target in docs project
.PHONY: docs-help
docs-help:
##  docs-help: List the individual commands in the documentation subproject.
	@echo "Commands in the documentation subproject:"
	$(MAKE) -C docs help --no-print-directory
	@echo "Run these commands from inside the 'docs/' directory."

# Override for `pymarkdownlnt-install` target in docs project. Make it a noop.
.PHONY: docs-pymarkdownlnt-install
docs-pymarkdownlnt-install:
	@echo "Cannot run 'docs-pymarkdownlnt'. This project doesn't use Markdown."

# Override for `lint-md` target in docs project. Make it a noop.
.PHONY: docs-lint-md
docs-lint-md:
	@echo "Cannot run 'docs-lint-md'. This project doesn't use Markdown."

# Passthrough for the rest of the targets in docs project
.PHONY: docs-%
docs-%: docs-install
	$(MAKE) -C docs $(@:docs-%=%) --no-print-directory

# Run our own docs linting, then pass to the docs
.PHONY: docs-lint
docs-lint: docs-install
##  docs-lint: Lint the documentation
ifneq ($(CI),)
	@echo ::group::$@
endif
	uv run $(UV_DOCS_GROUPS) sphinx-lint docs \
	--ignore docs/.sphinx \
	--ignore docs/_build \
	--ignore docs/reference/commands \
	--enable all \
	-d line-too-long,missing-underscore-after-hyperlink,missing-space-in-hyperlink
	$(MAKE) -C docs spelling --no-print-directory
	$(MAKE) -C docs woke --no-print-directory
	$(MAKE) -C docs linkcheck --no-print-directory
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
