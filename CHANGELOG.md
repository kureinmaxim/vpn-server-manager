# Changelog

All notable changes to VPN Server Manager. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [4.4.4] - 2026-09-03

### Fixed
- Add/Edit icon picker shows a live preview, has a **From screen** capture button, and actually saves the icon on Edit.

## [4.4.3] - 2026-09-03

### Fixed
- Double-click on a compact card now unarchives or expands it. The previous handler ignored the click because WebView selected the card text.

## [4.4.2] - 2026-09-03

### Improved
- Double-click an archived card to restore it; double-click again to open the previous full card (credentials, accordions).
- Fresh install defaults the UI to English (the language menu still switches to Russian or Chinese).

## [4.4.1] - 2026-09-03

### Improved
- Server list uses compact preview cards; drag the handle to reorder.
- Archive a card (list icon or Edit checkbox) to grey it out without deleting it.

## [4.4.0] - 2026-09-03

### Fixed
- English and Chinese Edit/Add forms no longer fall back to Russian for new password labels, the Set badge, or the native file-picker caption (Windows WebView always used the OS language).
- Footer and About show **Kurein M.N.** in English and Chinese, **Куреин М.Н.** in Russian.
- Root-password column on Edit is no longer faded when the SSH user is `root`; the hint under the field is enough.

## [4.3.8] - 2026-09-03

### Improved
- Edit/add server: SSH login password vs root-account password labels say which one Status uses.
- Password fields no longer draw mask dots on top of the placeholder (WebView/Chromium).
- Edit server form is a compact two-column layout with sticky Save, so it fits on one screen.

### Fixed
- Passwords with `%` / `&` (for example `...}&%:`) were shown or copied wrong after a reload because the WebView treated `%` in HTML attributes as URL-encoding. Secrets are now stored base64 in the page.

## [4.3.6] - 2026-09-02

### Fixed
- Windows installer now ships `templates/macros/` (and other template subfolders). After PIN login, 4.3.5 crashed with `TemplateNotFound: macros/credentials.html`.
- Installer welcome page uses plain text instead of raw `README.md` Markdown.

## [4.3.5] - 2026-09-02

### Changed
- Public docs: Russian-only `docs/`, English GitHub files in the repo root, English cheatsheet command labels for all UI languages.
- Version strings stay in sync through `tools/update_version.py` (`README_ru.md`, installer comment, `build_macos.py`, `docker-compose.yml`, bug-report placeholder).

## [4.3.4] - 2026-08-05

### Fixed
- SSH / panel / hoster passwords could be wrong after paste and copy (whitespace, line breaks, invisible characters, secrets in `onclick` breaking on quotes).

### Improved
- Secrets sanitized on save and load.
- Safe copy via `data-*` + `|tojson` (`static/js/credentials.js`).
- Add/edit forms: show/hide, copy, current password, “set” badge.
- Panel login saved on the add-server form (`panel_user`).
- Plaintext `*_decrypted` fields are no longer written to disk.

## [4.3.2] - 2026-06-25

### Added
- Monitoring for the TelegramOnly stack (VLESS/Hysteria2/MTProto/NaiveProxy/Tailscale, bot + HA, Reticulum bridge, Dockhand/Headplane over SSH tunnel).
- Container role highlighting in Status.
- Monitoring install checklist (only selected packages).
- `scripts/rotate_secret_key.py` for Fernet key rotation (`--dry-run`).

### Fixed
- Language switch compiles `.po` → `.mo` on startup.
- Install final check only counts selected utilities.
- Web-panel “Open” / tunnel only when the service is up.
- CI: removed no-op `build` job; tests remain.

### UI / i18n
- Tighter monitoring layout; security events use bootstrap icons.
- Service/port catalog aligned with TelegramOnly.
- EN + ZH strings for the new UI.

## [4.2.9] - 2026-06-15

### Fixed
- Monitoring install as **root** on minimal Debian: no `sudo` when `id -u` is 0; non-root still uses passwordless sudo. Fake “installed” ticks gone.

## [4.2.8] - 2026-06-15

### Fixed
- Install steps check apt/sudo exit codes (`_run` helper). Passwordless-sudo preflight. `DEBIAN_FRONTEND=noninteractive`.

## [4.2.7] - 2026-06-15

### Fixed
- Tool detection via `command -v` and `/usr/sbin` (not `which`).
- Storage mount table: `df -hP` so long device names wrap correctly.

## [4.2.6] - 2026-06-15

### Fixed
- macOS **405 Method Not Allowed** on add-server POST. Handler creates the server, encrypts credentials, optional icon/geo, and creates `data/servers.json.enc` if missing.

## [4.2.1] - 2026-04-06

### Added
- First-run PIN setup for packaged apps (custom PIN or default `1234`). Tests for PIN routes.

### Fixed
- Windows desktop “Leave site?” prompt: server-side desktop flag instead of `window.pywebview`.
- PIN routes share one runtime `config.json`.
- Windows installer no longer references removed `docs/WINDOWS_GUIDE.md`.
- Monitoring UFW hints use the real SSH port, not hardcoded 22. Dashboard layout restored.

### Changed
- Version tool: `tools/update_version.py` (`status` / `sync` / `bump`). Source of truth `config/config.json.template`.

## [4.0.10] - 2025-10-15

### Fixed
- Network stats sum **all** interfaces (eth/ens/wlan + tun/wg/tap), not only `eth0`.
- In-app navigation no longer shows “Leave site?”; closing the tab still warns.

## [4.0.7] - 2025-10-14

### Fixed
- Monitoring open delay (~40s): Flask `threaded=True` / werkzeug in desktop mode.
- Faster SSH timeouts for install checks; loading spinner shown immediately.
- SSH password decrypt via `data_manager.decrypt_data()` on all monitoring endpoints.
- PNG status snapshot uses real html2canvas.
- Uninstall buttons: duplicate handlers removed.

### Improved
- Metrics history 288 points (24h). Compact monitoring UI. EN/ZH strings.

## [4.0.6] - 2025-10-13

### Security
- Removed `.env`, `config.json`, and `data/*.enc` from git history; new `SECRET_KEY`.
- macOS build no longer packs `.env` / `config.json` into the DMG.
- Frozen app creates `.env` on first launch. See `SECURITY.md`.
- v4.0.5 GitHub release was pulled. Recreate `.env` with `python generate_key.py` if you cloned before 2025-10-13.

## [4.0.5] - 2025-10-12

### Fixed
- Save-as-PNG snapshot endpoint and html2canvas loading.
- Invalid-PIN message (`data.error`).
- SSH stats use the configured port. Import form typo.

## [4.0.4] - 2025-10-12

### Added
- `setup_windows.bat` / `start_windows.bat`. Docker guide notes for Windows/macOS. `.gitattributes` for line endings.

### Fixed
- `generate_key.py` no longer overwrites the whole `.env` (only `SECRET_KEY`).

## [4.0.3] - 2025-10-12

### Added
- Version read from config. Desktop launcher, `/pin/exit_app` / logout, `window.destroy()`.

### Fixed
- Frozen-app paths under Application Support / Logs. Session isolation. Hints 500 error. Footer server URL.

## [4.0.2] - 2025-10-12

### Added
- Multi-instance: OS-assigned port 0, unique session cookie, `/shutdown`. See [MULTI_APP_IMPLEMENTATION.md](MULTI_APP_IMPLEMENTATION.md).

## [4.0.1] - 2025-10-11

### Fixed
- PIN login JSON body (`application/json` instead of form-urlencoded).

## [4.0.0] - 2025-01-15

### Added
- Modular Flask app (factory, blueprints, services, tests, Docker). Entry points `run.py` / `run_desktop.py`.

## [3.7.3] - 2025-10-03

### Security
- “First run” PIN reset only on a clean install (not when data already exists).

### Changed
- Status modal layout (CPU/Memory grid, IPv6, tables).

### Fixed
- Duplicate disk mounts; fallback OS icon.

## [3.7.2] - 2025-10-02

### Added
- OS name from `/etc/os-release`. Save Status panel as PNG.

### Fixed
- Docker JSON parsing fallbacks. Inodes via `df -iP`.

## [3.7.1] - 2025-10-02

### Added
- Status modal (CPU, memory, disks, network, Docker) with 10s refresh. `GET /server/<id>/stats`.

## [3.6.9] - 2025-09-28

### Added
- IP owner (IP2Location). Expanded hints (NGINX/Docker/systemd). Info/software fields on cards.

## [3.6.7] - 2025-08-14

### Changed
- Docs split: product guides vs lessons (now `lessons/` in the repo root).

## [3.6.5] - 2025-08-08

### Added
- i18n tooling (`tools/auto_translate_po.py`). EN/ZH catalogs.

## [3.5.3] - 2025-08-04

### Added
- GitHub publication: CI, issue/PR templates, `SECURITY.md`. Developer name anonymized in docs; default PIN `1234`.

## [3.5.2] / [3.4.0] - 2025-08

PIN lock, offline indicator, macOS icon conversion, key management, import/export, UI zoom.

## [3.3.x] – [3.0.0] - 2025-06–07

Encryption key rotation, export variants, hints, Fernet vault, PyWebView GUI.

## [2.0.0] - 2025-05-15

Flask web UI.

## [1.0.0] - 2025-05-01

First console release, JSON storage.
