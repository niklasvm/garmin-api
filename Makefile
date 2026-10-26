.PHONY: sync browser run explore report message message-send lint pi-install

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

# On the Pi: install and start the daily systemd timer (user units, see README)
pi-install:
	mkdir -p ~/.config/systemd/user
	cp deploy/morning-report.service deploy/morning-report.timer ~/.config/systemd/user/
	systemctl --user daemon-reload
	systemctl --user enable --now morning-report.timer
