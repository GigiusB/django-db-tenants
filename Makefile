BUILDDIR='.build'
PYTHONPATH:=${PWD}/tests/:${PWD}:${PYTHONPATH}
BUILDDIR?=./.build
CURRENT_BRANCH:=$(shell git rev-parse --abbrev-ref HEAD)
.PHONY: help runonce run i18n
.DEFAULT_GOAL := help
CORES?=$(shell (nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1) | awk '{ v = int($$1 * 0.75); print (v < 1 ? 1 : v) }')

ifeq ($(wildcard .python-version),)
    PYTHON_VERSION = ""
else
    PYTHON_VERSION = $(shell head -1 .python-version)
endif

ifeq ($(wildcard .initialized),)
    INITIALIZED = 0
else
    INITIALIZED = 1
endif

guard-%:
	@if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
        exit 1; \
    fi


define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z0-9_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

lint:  ## code lint
	pre-commit run --all-files

clean: ## clean development tree
	rm -fr ${BUILDDIR} build dist src/*.egg-info .coverage coverage.xml .eggs .pytest_cache *.egg-info
	find src -name __pycache__ -o -name "*.py?" -o -name "*.orig" -prune | xargs rm -rf
	find tests -name __pycache__ -o -name "*.py?" -o -name "*.orig" -prune | xargs rm -rf

fullclean:  clean  ## More aggressive file cleaning
	rm -fr .tox .cache .venv
	$(MAKE) clean

test:
	pytest tests/

outdated:  ## Generates .outdated.txt and .tree.txt files
	uv tree > .tree.txt
	uv pip list --outdated > .outdated.txt

act-docs:
	act -W '.github/workflows/docs.yml' push --job generate
	cd .artifacts/1/github-pages && tar -xzvf github-pages.zip
