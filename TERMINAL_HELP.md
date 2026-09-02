# Terminal commands

Language: **English** · [Русский](TERMINAL_HELP_ru.md)

Commands for running VPN Server Manager from a terminal. Replace `/path/to/vpn-server-manager` with your clone directory. Never commit a personal home path.

Requires **Python 3.13+**.

## 1. Go to the project

```bash
cd /path/to/vpn-server-manager
```

After `git clone https://github.com/kureinmaxim/vpn-server-manager.git` that directory is usually `./vpn-server-manager`.

## 2. Virtual environment

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` in the prompt.

## 3. First-time setup

```bash
python -m pip install -r requirements.txt
cp env.example .env          # Windows: copy env.example .env
python generate_key.py
cp config/config.json.template config.json   # Windows: copy config\config.json.template config.json
python -m babel.messages.frontend compile -d translations
```

## 4. Run

```text
Web:     python run.py
Desktop: python run_desktop.py
Debug:   python run.py --debug
```

One-liner (macOS / Linux):

```bash
cd /path/to/vpn-server-manager && source venv/bin/activate && python3 run.py
```

One-liner (Windows PowerShell):

```powershell
cd \path\to\vpn-server-manager; .\venv\Scripts\Activate.ps1; python run.py
```

---

## Dependencies

```bash
pip install package_name
pip install -r requirements.txt
```

Prefer editing `requirements.txt` by hand over `pip freeze` so pin ranges stay intact.

---

## Data and encryption

Create a key if `.env` is missing:

```bash
python generate_key.py
```

Show the key (keep this private):

```bash
# macOS / Linux
cat .env

# Windows PowerShell
Get-Content .env
```

Decrypt / inspect data (if the tool is present):

```bash
python tools/decrypt_tool.py
```

---

## Build

```powershell
# Windows installer
.\build_windows.ps1
```

```bash
# macOS .app + .dmg
source venv/bin/activate
python3 build_macos.py
```

Full steps: [BUILD.md](BUILD.md) · [BUILD_ru.md](BUILD_ru.md)

---

## Git (short)

```bash
git status
git diff
git add .
git commit -m "Describe the change"
git log --oneline
```

Do not `git add` `.env`, `config.json`, or `data/`.

---

## Diagnostics

Default web port is **5050**:

```bash
# macOS / Linux
lsof -i :5050
lsof -ti:5050 | xargs kill -9
```

```powershell
# Windows
netstat -ano | findstr :5050
```

---

## Optional aliases

Put **your** clone path in the alias — not a username from this repo.

**zsh** (`~/.zshrc`):

```bash
REPO="$HOME/vpn-server-manager"
alias vpn-cd="cd \"$REPO\""
alias vpn-run="cd \"$REPO\" && source venv/bin/activate && python3 run.py"
alias vpn-desk="cd \"$REPO\" && source venv/bin/activate && python3 run_desktop.py"
```

**PowerShell** (`$PROFILE`):

```powershell
$VpnRepo = Join-Path $HOME "vpn-server-manager"
function vpn-cd { Set-Location $VpnRepo }
function vpn-run { Set-Location $VpnRepo; .\venv\Scripts\Activate.ps1; python run.py }
```

---

## Troubleshooting

```bash
# Recreate venv
rm -rf venv                 # Windows: rmdir /s /q venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

PyWebView on macOS:

```bash
pip install --upgrade pywebview
```

Proxy errors while installing packages: [WINDOWS_PROXY_TROUBLESHOOTING_ru.md](docs/WINDOWS_PROXY_TROUBLESHOOTING_ru.md)

---

## More docs

- [README.md](README.md)
- [BUILD.md](BUILD.md)
- [SECRET_KEY_ru.md](docs/SECRET_KEY_ru.md)
- [INDEX_ru.md](docs/INDEX_ru.md)
