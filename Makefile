UV ?= uv
CODEX ?= codex

.PHONY: setup test install-local-mcp install-local-plugin
setup:
	$(UV) sync --locked
	$(UV) run --locked playwright install chromium

test:
	$(UV) run --locked python -m unittest discover -s tests

install-local-mcp:
	$(CODEX) mcp add teams-mcp --env "DISPLAY=$(DISPLAY)" --env "WAYLAND_DISPLAY=$(WAYLAND_DISPLAY)" --env "XDG_RUNTIME_DIR=$(XDG_RUNTIME_DIR)" -- "$(CURDIR)/.venv/bin/teams-mcp"

install-local-plugin: setup
	$(CODEX) plugin marketplace add "$(CURDIR)" --json
	$(CODEX) plugin add teams-mcp@teams-mcp-repo --json
	$(MAKE) install-local-mcp
