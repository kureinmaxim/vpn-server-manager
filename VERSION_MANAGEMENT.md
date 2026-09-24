# Version management

How VPN Server Manager stores the app version, how to change it safely, and which files stay in sync.

Related: [BUILD.md](BUILD.md) · [release_guide_ru.md](docs/release_guide_ru.md) · [CHANGELOG.md](CHANGELOG.md)

## Source of truth

The only release-version source of truth is `config/config.json.template`:

```json
{
  "app_info": {
    "version": "4.4.4",
    "release_date": "03.09.2026",
    "last_updated": "2026-09-03"
  }
}
```

Do **not** take the version from `%APPDATA%`, `~/Library/Application Support`, a local `config.json`, or `APP_VERSION` in the environment. Those are runtime settings for one machine.

## What the tool syncs

`tools/update_version.py` updates:

- `config/config.json.template`
- `README.md`
- `vpn-manager-installer.iss`
- `env.example`
- `app/config.py`
- `app/__init__.py`
- `setup.py`
- `build_macos.py`
- `docker-compose.yml`

Compatible wrapper: `tools/bump_version.py`.

```text
python tools/update_version.py status
python tools/update_version.py sync
python tools/update_version.py sync X.Y.Z
python tools/update_version.py bump patch|minor|major
```

Flags: `--release-date DD.MM.YYYY`, `--last-updated YYYY-MM-DD`, `--dry-run`.

The script uses only the Python standard library. A project virtual environment is not required.

## Examples

Windows, from the project root:

```powershell
python tools\update_version.py status
python tools\update_version.py bump patch
python tools\update_version.py sync X.Y.Z
```

Use `.\venv\Scripts\python.exe` or `.\.venv\Scripts\python.exe` only when that folder exists. This repository does not ship a `venv`, so that path fails with `The term '.\venv\Scripts\python.exe' is not recognized`.

macOS / Linux:

```bash
python3 tools/update_version.py status
python3 tools/update_version.py bump patch
```

After a version change: update `CHANGELOG.md`, run `status`, then build.

Build scripts read the version from `config/config.json.template` (`build_windows.ps1`, `build_macos.py`, `setup.py`).

## Troubleshooting

**`status` reports drift** — run `sync`.

**PowerShell: `.\venv\Scripts\python.exe` is not recognized** — there is no `venv` folder. Run `python tools\update_version.py status` instead.

**PowerShell: The module 'venv' could not be loaded** — the command was started without `.\`. Prefer `python tools\update_version.py`.

**UI version ≠ installer version** — check `config/config.json.template`, `vpn-manager-installer.iss`, `README.md`, and `status`. Someone edited one file by hand.

**Packaged app in `%APPDATA%` shows an old version** — rebuild after syncing. The user config is not the release source of truth.

## Rule

Change versions only through `tools/update_version.py`. Keep the source of truth in `config/config.json.template`. Always run `status` before a release.
