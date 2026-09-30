# Version management

How VPN Server Manager stores the app version, how to change it safely, and which files stay in sync.

Related: [BUILD.md](BUILD.md) · [release_guide_ru.md](docs/release_guide_ru.md) · [CHANGELOG.md](CHANGELOG.md)

## Source of truth

The only release-version source of truth is `config/config.json.template`:

```json
{
  "app_info": {
    "version": "X.Y.Z",
    "release_date": "DD.MM.YYYY",
    "last_updated": "YYYY-MM-DD"
  }
}
```

Do **not** take the version from `%APPDATA%`, `~/Library/Application Support`, a local `config.json`, or `APP_VERSION` in the environment. Those are runtime settings for one machine.

## Commands

`tools/update_version.py` uses only the Python standard library; no virtual environment is required.

| Command | Version | Release dates |
|---|---|---|
| `status` | shows every tracked file | — |
| `bump patch\|minor\|major` | next semantic version | set to today |
| `sync X.Y.Z` | sets `X.Y.Z` | set to today |
| `sync` | re-applies the current source version | kept from the source |

Flags for `bump` and `sync`: `--release-date DD.MM.YYYY`, `--last-updated YYYY-MM-DD`, `--dry-run` (show what would change, write nothing).

`bump` and `sync` print the target first, then every updated file:

```text
Target version:      4.9.1
Target release date: 30.09.2026
Target last updated: 2026-09-30

Updated config/config.json.template
Updated README.md
...
```

Compatible wrapper: `tools/bump_version.py --bump patch` or `--version X.Y.Z`.

## What the tool syncs

`sync` and `bump` update, and `status` checks:

| `status` label | File | What changes |
|---|---|---|
| `template` / `source` | `config/config.json.template` | `app_info` version and dates |
| `readme` | `README.md` | `# VPN Server Manager vX.Y.Z` |
| `installer` | `vpn-manager-installer.iss` | header comment and `MyAppVersion` |
| `env` | `env.example` | `APP_VERSION=` |
| `app_config` | `app/config.py` | default `APP_VERSION` and the generated `.env` line |
| `app_init` | `app/__init__.py` | fallback `app_info` (version and dates) |
| `setup` | `setup.py` | fallback versions |
| `macos` | `build_macos.py` | fallback versions |
| `compose` | `docker-compose.yml` | header and `APP_VERSION=` |
| `bug_form` | `.github/ISSUE_TEMPLATE/bug.yml` | version placeholder |

The `local` row is a `config.json` in the project root. It is optional: `INFO MISSING` is normal. If the file exists, the tool updates it too.

Not synced on purpose: `CHANGELOG.md` (written by hand), version mentions in `docs/` (history), and `installer_output/checksum.txt` (changes only after a Windows installer build).

## Release checklist

1. Bump the version:
   ```bash
   python3 tools/update_version.py bump patch
   ```
   On Windows: `python tools\update_version.py bump patch`.
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` (same date as `last_updated`).
3. Check that nothing drifted:
   ```bash
   python3 tools/update_version.py status
   ```
   Every row except `local` must be `OK`.
4. Run the tests, commit, push.
5. Build: `build_macos.py` / `build_windows.ps1` read the version from `config/config.json.template`. After a Windows build, commit the refreshed `installer_output/checksum.txt`.

## Python on each system

macOS / Linux: `python3 tools/update_version.py …` works everywhere. The project `venv/` (if you created one) also works: `venv/bin/python tools/update_version.py …`.

Windows, from the project root: `python tools\update_version.py …`. Use `.\venv\Scripts\python.exe` only when that folder exists on your machine. `venv/` is local and never committed, so a fresh clone does not have it.

## Troubleshooting

**`status` shows `DIFF`** — someone edited a file by hand. Run `sync` (keeps the source version and dates).

**`RuntimeError: Could not update …` while syncing** — the line the tool looks for was reformatted. Restore the expected form (see the table above) and run `sync` again.

**PowerShell: `.\venv\Scripts\python.exe` is not recognized** — there is no `venv` folder. Run `python tools\update_version.py status` instead.

**PowerShell: The module 'venv' could not be loaded** — the command was started without `.\`. Prefer `python tools\update_version.py`.

**UI version ≠ installer version** — run `status`; rebuild after syncing.

**Packaged app shows an old version** — rebuild and reinstall. The user `config.json` in `%APPDATA%` / `~/Library/Application Support` is not the release source of truth.

## Rule

Change versions only through `tools/update_version.py` — never with search-and-replace across the repository. Keep the source of truth in `config/config.json.template`. Always run `status` before a release.
