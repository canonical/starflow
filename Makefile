.PHONY: help
help:
	@echo "Usage:"
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'

.PHONY: lint
lint:
## lint: Lint the codebase with Prettier
	npx prettier --print-width=99 --check .
	bash ${CURDIR}/.github/shellcheck-actions.sh

.PHONY: format
format:
## format: Formats both Markdown documents and YAML documents to preferred repository style.
	npx prettier --print-width=99 --write .

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

.PHONY: test-coverage
test-coverage:
	$(info Simulating coverage creation)
	$(info "Running tests with extra pytest options: ${PYTEST_ADDOPTS}")
	uvx coverage run .test-data/hello.py
	uvx coverage xml -o coverage.xml
