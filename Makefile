.PHONY: sync browser run explore report message message-send lint

sync:
	uv sync --frozen

browser:
	uv run --frozen playwright install chromium

run:
	uv run --frozen garmin-api

explore:
	uv run --frozen explore

message:
	uv run --frozen message --dry-run

message-send:
	uv run --frozen message

report:
	uv run --frozen report

lint:
	uvx ruff check src
	uvx ruff format --check src
