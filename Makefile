.PHONY: default format lint install check venv

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
