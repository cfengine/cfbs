.PHONY: default format lint install check venv coverage

default: check

venv:
	uv venv --clear
	uv sync

format: venv
	uv tool run black cfbs/ tests/

lint: venv
	uv tool run black --check cfbs/ tests/ --fast
	uv run flake8 cfbs/ tests/ --extend-exclude=tests/tmp --ignore=E203,W503,E722,E731 --max-complexity=100 --max-line-length=160
	uv tool run pyright cfbs/

install:
	pipx install --force --editable .

check: venv format lint
	uv run pytest

coverage: export COVERAGE_PROCESS_START = $(PWD)/.coveragerc
coverage: export COVERAGE_FILE = $(PWD)/.coverage
coverage:
	uv run coverage erase
	uv run coverage run --parallel-mode -m pytest
	uv run bash tests/shell/all.sh
	uv run coverage combine
	uv run coverage report --fail-under=50
	uv run coverage xml
