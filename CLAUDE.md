# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

VPN Server Manager: a Flask app that keeps an encrypted local inventory of VPS servers (credentials, DNS providers/domains) and inspects or manages them over SSH (paramiko). It shows load, Tailscale mesh/DERP diagnostics, tracked projects, DNS/Chatmail roles, and runs reset/service-control operations. It runs as a local web server or inside a native pywebview window (`desktop/`). UI languages: Russian (source), English, Chinese.

## Commands

```bash
python run.py                  # web mode, 127.0.0.1, first free port from $PORT (default 5000)
python run.py --debug          # DevelopmentConfig
python run.py --desktop        # pywebview window (same as run_desktop.py)

pytest                                              # all tests (config in pytest.ini)
pytest tests/test_services/test_dns_registry.py     # one file
pytest tests/test_routes/test_dns.py::test_name     # one test
pytest --no-cov tests/...                           # skip coverage when running a subset

make lint      # flake8 app tests && bandit -r app
make format    # black + isort
python tools/check_public_files.py   # fails if private files (.env, *.enc, config.json, data/*.json) are tracked or in package dirs
```

- `pytest.ini` always adds `--cov=app --cov-fail-under=34`. That threshold is a ratchet: it records current coverage, not a target. Running a single test file with coverage on will fail the threshold, so use `--no-cov`.
- CI (`.github/workflows/ci.yml`) runs `python generate_key.py` and then `pytest`. There is no lint step in CI.
- First-time setup: `cp env.example .env && python generate_key.py && cp config/config.json.template config.json`. `.mo` files are gitignored and are compiled from `.po` automatically in `create_app` (`compile_translations`).

## Versioning and releases

- The single source of truth for the version is `app_info` in `config/config.json.template`. Never edit version strings by hand. Use `python3 tools/update_version.py bump patch|minor|major` (or `sync X.Y.Z`, `status`). It updates README, `app/__init__.py`, `app/config.py`, `setup.py`, `build_macos.py`, `env.example`, `docker-compose.yml`, the Inno Setup `.iss` and the bug issue template.
- `CHANGELOG.md` is written by hand (Keep a Changelog). Each release gets a `## [X.Y.Z] - YYYY-MM-DD` section. The README "Latest patch" blurb is also updated by hand.
- Commit subjects follow a pattern: a user-facing description, then `; bump to X.Y.Z` when the version changes.
- Packaging is done locally, not in CI: `build_macos.py` (PyInstaller `VPNServerManager-Clean.spec`), `build_windows.ps1` plus `vpn-manager-installer.iss`. See `BUILD.md` and `VERSION_MANAGEMENT.md`.

## Architecture

**App factory** (`app/__init__.py:create_app`): loads `config_by_name[...]` from `app/config.py`, sets up Babel (`get_locale`: `?lang=` → session → saved UI prefs → default), registers services, then blueprints (`main`, `api`/`pin`/`vendor`, `reset`, `server_control`, `net_tools`, `dns_mail`, `dns`). A large `context_processor` injects `app_info`, tracked projects, locale, zoom and desktop flag into every template.

**Service registry** (`app/services/__init__.py`): a class-level dict used for DI. `register_services` adds `ssh`, `crypto`, `api` and, only if `SECRET_KEY` is a valid Fernet key, `data_manager`. Routes call `registry.get('data_manager')` and must handle `None` (invalid or missing key). Tests clear the registry before and after each test (`tests/conftest.py`), so code must not hold on to service instances across requests.

**Data storage** (`DataManagerService`): servers *and* the DNS card (providers, domains, records, own DNS) live in one Fernet-encrypted `.enc` file. Its path comes from `active_data_file` in the runtime `config.json`. Use `load_servers`/`save_servers` and `load_dns`/`save_dns`, which share the payload format (`split_payload`/`read_payload`). Passwords inside servers are encrypted again at field level. `normalize_server_data` migrates old records. `_strip_runtime_secrets` keeps transient values off disk.

**Paths depend on frozen vs dev**: in dev, `APP_DATA_DIR` is the repo root and `.env`/`config.json` live there. In a PyInstaller build they live in `~/Library/Application Support/VPNServerManager-Clean/` (macOS), `%APPDATA%\VPNServerManager-Clean\` (Windows) or `~/.local/share/...`. `app/config.py` creates `.env` with a fresh key on first frozen launch. Always resolve paths through `app.config` (`APP_DATA_DIR`, `DATA_DIR`, `UPLOAD_FOLDER`) and never relative to cwd.

**Auth**: a PIN lock based on session flags (`app/utils/decorators.py`: `require_auth`, `require_pin`). `is_api_request()` decides between a JSON 401 and a redirect to `main.index_locked`. Session cookies are deliberately non-secure, non-HttpOnly and SameSite=None because pywebview on Windows needs them.

**SSH layer**: `app/services/ssh_service.py` (the largest module) holds pooled connections, closed on exit via `run.py`'s atexit hook. `ssh_auth.py` resolves password/key/passphrase from a server card (key text or `~/.ssh` path, key first and password as fallback). There are two host-key policies on purpose. Read-only monitoring and load accept unknown hosts. Destructive or deep operations (`routes/reset.py`, `server_control`, disk usage, archive cleanup) use strict `known_hosts` + `RejectPolicy` and translate failures into user-facing reasons (`describe_failure`). Keep new mutating operations on the strict path.

**Remote features as payload/probe modules**: most remote functionality is split into a pure "payload" or "context" builder and a thin route. Examples: `*_payload.py` builds the shell/Python script sent over SSH, `*_probe.py`/`*_context.py` parse output, and `protocol_*`/`*_mutations.py` edit VPN protocol configs (Xray, Hysteria, Naive). Tests mostly target these pure functions with SSH mocked, so new remote logic should follow the same split.

**Tracked projects / roles**: `services/project_stats.py` (`load_projects`, `FILE_MANAGER`, `CHATMAIL`), `dns_mail_probe.ROLE_NAMES` and `remote_derp` define which systemd units, containers and processes identify a project. Cards, Projects, Server load and Monitoring all read from these definitions.

## Conventions

- Code comments, docstrings and log messages are mostly in Russian. User-facing strings are Russian `gettext` msgids (`_("…")`) with translations in `translations/{en,zh}/LC_MESSAGES/messages.po` (there is no `ru` catalog). When you add or change a UI string, add the `en` and `zh` entries to the `.po` files. `tools/auto_translate_po.py` can fill gaps.
- Tests and docs use documentation IPs and domains (e.g. `192.0.2.x`, `example.com`), never real infrastructure.
- Never commit `.env`, `*.enc`, `config.json` or `data/*.json`. `tests/test_privacy_packaging.py` also checks that installers ship `config/hints.json.template` and no user data.
- `memory-bank/`, `.cursor/rules/` and `lessons/` hold Cursor workflow material and personal notes. They are not application code.
