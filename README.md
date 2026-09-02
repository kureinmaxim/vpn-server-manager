# VPN Server Manager v4.3.6

Language: **English** · [Русский](README_ru.md)

<p align="center">
  <img src="static/VPSc.png" alt="VPN Server Manager" width="220">
</p>

<p align="center">
  <strong>A local desktop app for people who actually run VPN servers.</strong><br>
  Encrypted inventory, SSH monitoring, PIN lock — no cloud account.
</p>

<p align="center">
  <a href="https://github.com/kureinmaxim/vpn-server-manager/releases"><img src="https://img.shields.io/github/v/release/kureinmaxim/vpn-server-manager?style=flat-square" alt="Latest release"></a>
  <a href="https://github.com/kureinmaxim/vpn-server-manager/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/kureinmaxim/vpn-server-manager/ci.yml?style=flat-square" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-0F766E?style=flat-square" alt="MIT License"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/python-3.13+-3776AB?style=flat-square" alt="Python 3.13+"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-1F2937?style=flat-square" alt="Windows, macOS, Linux">
</p>

VPN Server Manager keeps server logins, panel credentials, and hoster details in an encrypted local vault. It opens as a native desktop window (`Flask` + `PyWebView`) or in a browser. Monitoring talks to the machine over SSH — there is no always-on agent.

## What you get

| | |
|---|---|
| **Encrypted vault** | Fernet encryption for server data. Import / export full backups. Lose the key, lose the data — by design. |
| **Desktop or browser** | Native window on Windows, macOS, and Linux, or `python run.py` for web mode. |
| **PIN lock** | Quick lock on the local app so a shared machine is not an open notebook. |
| **SSH monitoring** | Live traffic, firewall, systemd services, Docker, security events, CPU/RAM history. Knows TelegramOnly, Reticulum, and web panels (Dockhand, Headplane) over an SSH tunnel. |
| **Works offline** | The inventory stays usable without internet. Network-only actions disable themselves cleanly. |
| **Languages** | Russian, English, and Chinese. `.po` catalogs compile on first launch. |

## Quick start

**Requires Python 3.13+.**

### Windows

```cmd
setup_windows.bat
start_windows.bat
```

Or in PowerShell:

```powershell
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

copy env.example .env
python generate_key.py
copy config\config.json.template config.json

python -m babel.messages.frontend compile -d translations
python run.py
```

### macOS / Linux

```bash
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager

python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt

cp env.example .env
python3 generate_key.py
cp config/config.json.template config.json

python -m babel.messages.frontend compile -d translations
python3 run.py
```

### Run

```text
Web:     python run.py
Desktop: python run_desktop.py
Debug:   python run.py --debug
```

Installers (Windows setup `.exe`, macOS `.dmg`) are on the [Releases](https://github.com/kureinmaxim/vpn-server-manager/releases) page. Build steps: [BUILD.md](BUILD.md).

## Safety notes

- Default PIN in the template is `1234`. Change it before real use.
- Keep `.env` (`SECRET_KEY`) and encrypted exports off shared drives and out of git.
- There is no password recovery. A full export is the backup.

## Docs

- [Documentation index](docs/INDEX_ru.md) (Russian)
- [Build guide](BUILD.md) · [RU](BUILD_ru.md)
- [Terminal help](TERMINAL_HELP.md) · [RU](TERMINAL_HELP_ru.md)
- [Version management](VERSION_MANAGEMENT.md) · [RU](VERSION_MANAGEMENT_ru.md)
- [Release process](docs/release_guide_ru.md) (Russian)
- [Monitoring](docs/README_MONITORING_ru.md) (Russian)
- [Docker](docs/DOCKER_GUIDE_ru.md) (Russian)
- [Changelog](CHANGELOG.md)
- [Lessons](lessons/README.md) (Russian: app + Git)

Questions: [Discussions](https://github.com/kureinmaxim/vpn-server-manager/discussions). Bugs: [Issues](https://github.com/kureinmaxim/vpn-server-manager/issues).

## License

[MIT](LICENSE)
