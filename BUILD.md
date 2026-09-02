# VPN Server Manager build guide

Language: **English** · [Русский](BUILD_ru.md)

How to build the **Windows installer** and the **macOS app**.

## Two build models

| Platform | Output | Does the user need Python? |
|----------|--------|----------------------------|
| **Windows** | Source installer (Inno Setup): `VPN-Server-Manager-Setup-vX.Y.Z.exe`. It unpacks the project, creates a `venv`, and installs dependencies. | **Yes.** Python 3.13+ must be on the machine. |
| **macOS** | Standalone `.app` (PyInstaller) + `.dmg`. Python and deps are inside the bundle. | No. |

> Windows does **not** ship a PyInstaller `.exe` of the app itself. The `.exe` is the **installer**. It runs `setup_windows.bat` and starts the app with `start_windows.bat`.

## Requirements

- Python 3.13+ and `pip`
- **Inno Setup 6** for the Windows installer — https://jrsoftware.org/isdl.php  
  Scripts expect `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` (change `$IsccPath` / `ISCC_PATH` in `build_windows.ps1` / `.bat` if yours differs)
- macOS + Xcode CLT (`sips`, `iconutil`) for `.app`
- A `venv` with `requirements.txt` installed (system `python3` is not enough for the macOS build)

## Environment (macOS / Linux)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

In this doc, `python` / `python3` means the **activated venv**. Without activation on macOS/Linux: `venv/bin/python3 …`.

Windows (PowerShell): `.\venv\Scripts\Activate.ps1`

---

## Step 1. Bump the version (use the tool)

Never edit version strings by hand. `tools/update_version.py` updates `config/config.json.template`, `vpn-manager-installer.iss` (`MyAppVersion`), `README.md`, `README_ru.md`, `env.example`, `app/config.py`, `app/__init__.py`, `setup.py`, `build_macos.py`, `docker-compose.yml`, and the bug-report template. Then add a `[X.Y.Z]` heading in `CHANGELOG.md`.

```bash
python tools/update_version.py status
python tools/update_version.py bump patch
python tools/update_version.py sync X.Y.Z
```

> If `config/config.json.template` and `vpn-manager-installer.iss` disagree, Inno writes one filename and `build_windows.ps1` looks for another → `Installer not found`. Always use `update_version.py`.

## Step 2. Compile translations (`.po` → `.mo`)

`.mo` files are gitignored. Without them, language switching fails and the installer ships an English-only UI.

```bash
python -m babel.messages.frontend compile -d translations
```

`build_windows.ps1` does this automatically.

---

## Step 3. Build

### Windows installer

```powershell
.\build_windows.ps1
```

or CMD: `build_windows.bat`

Output:

```text
installer_output/VPN-Server-Manager-Setup-vX.Y.Z.exe
installer_output/checksum.txt
```

On the user's machine the installer:

1. Checks for Python (and points at python.org + “Add to PATH” if missing)
2. Installs into `%LOCALAPPDATA%\Programs\VPN Server Manager`
3. Runs `setup_windows.bat` (`venv` + `requirements.txt`, a few minutes)
4. Creates Start Menu / desktop shortcuts to `start_windows.bat`

User data (`.env`, `config.json`, `data\`) is **not** in the installer and is **not** removed on upgrade/uninstall unless the user chooses that.

### macOS `.app` + `.dmg`

```bash
source venv/bin/activate
python3 build_macos.py
```

or `venv/bin/python3 build_macos.py`

Artifacts:

```text
dist/VPNServerManager-Clean.app
dist/VPNServerManager-Clean_Installer.dmg
```

---

## Local development (no installer)

```bash
python -m venv venv
# Windows:  .\venv\Scripts\Activate.ps1     |  macOS/Linux:  source venv/bin/activate
python -m pip install -r requirements.txt

cp env.example .env
python generate_key.py
cp config/config.json.template config.json
python -m babel.messages.frontend compile -d translations

python run.py
python run_desktop.py
python run.py --debug
```

Local files (not in git): `.env`, `config.json`, `translations/**/*.mo`.

Release version source of truth: `config/config.json.template`.

## Tests

```bash
pytest
pytest --cov=app tests/
```

## Common problems

**`ModuleNotFoundError: No module named 'dotenv'` (macOS)** — `build_macos.py` was run with system `python3`. Use the venv.

**`Installer not found`** — version mismatch. `python tools/update_version.py status` then `set X.Y.Z`.

**Inno Setup not found** — install Inno Setup 6 or fix `ISCC.exe` in `build_windows.ps1`.

**Languages do not switch** — compile `.mo` (step 2) and restart.

**`ProxyError` / `No matching distribution found`** — [WINDOWS_PROXY_TROUBLESHOOTING_ru.md](docs/WINDOWS_PROXY_TROUBLESHOOTING_ru.md)

**PowerShell will not run `venv\Scripts\python.exe`** — use `.\venv\Scripts\python.exe`.

## Related

- [README.md](README.md) · [README_ru.md](README_ru.md)
- [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md) · [VERSION_MANAGEMENT_ru.md](VERSION_MANAGEMENT_ru.md)
- [release_guide_ru.md](docs/release_guide_ru.md)
- [TERMINAL_HELP.md](TERMINAL_HELP.md)
