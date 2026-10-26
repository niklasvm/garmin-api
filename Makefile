.PHONY: sync browser run explore report message message-send lint pi-setup

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

# On the Pi, from the repo: install dependencies and start the daily systemd timer
pi-setup:
	@test -f .env || { echo "Copy .env into $(CURDIR) first"; exit 1; }
	uv sync --frozen --no-dev
	uv run --frozen --no-dev playwright install --with-deps chromium
	sudo loginctl enable-linger $(USER)
	mkdir -p ~/.config/systemd/user
	sed -e "s|@REPO@|$(CURDIR)|g" -e "s|@UV@|$$(command -v uv)|g" deploy/morning-report.service > ~/.config/systemd/user/morning-report.service
	cp deploy/morning-report.timer ~/.config/systemd/user/
	systemctl --user daemon-reload
	systemctl --user enable --now morning-report.timer
	systemctl --user list-timers morning-report.timer
