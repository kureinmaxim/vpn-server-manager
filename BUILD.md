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

Never edit version strings by hand. `tools/update_version.py` updates `config/config.json.template`, `vpn-manager-installer.iss` (`MyAppVersion`), `README.md`, `env.example`, `app/config.py`, `app/__init__.py`, `setup.py`, `build_macos.py`, `docker-compose.yml`, and the bug-report template. Then add a `[X.Y.Z]` heading in `CHANGELOG.md`.

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

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
python3 tools/build_macos_compatible.py
```

The launcher downloads isolated CPython **3.13.12** into `.build-python`, creates
`.venv-macos`, and syncs `requirements/macos-arm64.lock` with required hashes.
It does not use Homebrew Python for the application runtime or alter the normal
`venv`. Runtime/build packages are separated from developer tools. Native packages
must use wheels; the sole source exception is the pure-Python `proxy-tools` package,
whose source archive is hash-locked. uv's build-isolation tooling is not fully locked;
this is not a claim of byte-identical reproducible builds.

Current target: **Apple Silicon, macOS 13+**. Every collected Mach-O must have a
minimum deployment target no higher than 13.0; a newer dependency fails the build
before signing/packaging. The plist never promises an OS older than the selected
target. A runtime self-check loads native UI/crypto dependencies and performs a
synthetic encryption round trip without loading a profile or opening a window.
This runs on the build host; real GUI testing on macOS 13 is still required.

Intel builds are explicitly unavailable in this workflow: `cryptography 50` removed
macOS x86_64 wheels ([upstream changelog](https://cryptography.io/en/stable/changelog/)).
The launcher fails clearly on Intel instead of silently downgrading cryptography.
An Intel toolchain requires separate dependency/build and security review.

For maintenance, refresh the ARM lock with uv on macOS, then rebuild and test:

```bash
MACOSX_DEPLOYMENT_TARGET=13.0 uv pip compile requirements/macos-build.in \
  --python .build-python/cpython-3.13.12-macos-aarch64-none/bin/python3.13 \
  --python-platform aarch64-apple-darwin --only-binary :all: \
  --no-binary proxy-tools --generate-hashes -o requirements/macos-arm64.lock
```

`python3 build_macos.py` remains a low-level entry point using the current
interpreter, but now rejects binaries requiring more than macOS 13 by default.
Setting `MACOSX_DEPLOYMENT_TARGET` changes the build ceiling, not existing binaries.

Artifacts:

```text
dist/macos-local/VPNServerManager-Clean.app
dist/macos-local/VPNServerManager-Clean-X.Y.Z-arm64-local.dmg
dist/macos-local/VPNServerManager-Clean-X.Y.Z-arm64-local.json
```


The builder currently produces **local development artifacts only** (ad-hoc signed,
not notarized). It reads the version from the tracked template, never copies the
project configuration into the user's installed profile, and uses dedicated
`build/macos-local` / `dist/macos-local` directories. Rebuilding replaces those two
directories; older outputs elsewhere and the installed application are untouched.

After PyInstaller, it merges the final plist, derives architecture and the highest
minimum OS from all collected Mach-O deployment targets, signs the outer bundle,
and requires `codesign --verify --deep --strict`. All collected binaries must
support the executable's architectures. DMG staging preserves symlinks and verifies
the staged signature; `hdiutil verify` must also succeed. The JSON manifest records
the actual architecture, minimum binary target, signing status and DMG SHA-256.
That target is a lower bound, **not a tested minimum supported macOS version**.

Public release gates remain: Developer ID signing of nested code and the outer
bundle with hardened runtime, notarization, stapling, Gatekeeper assessment, then
clean-Mac launch/upgrade/restore tests. Do not publish a `-local` image as a trusted
release or advise users to disable Gatekeeper. No upload to Apple or GitHub is
performed by this builder. Follow [Apple signing guidance](https://developer.apple.com/library/archive/technotes/tn2206/)
and [PyInstaller macOS notes](https://pyinstaller.org/en/stable/feature-notes.html).

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

- [README.md](README.md)
- [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)
- [release_guide_ru.md](docs/release_guide_ru.md)
- [TERMINAL_HELP.md](TERMINAL_HELP.md)


## macOS CI evidence

The `macos-build` job uses an ARM `macos-15` runner and uv 0.10.7, builds with the
same isolated launcher, then runs:

```bash
.venv-macos/bin/python tools/check_public_files.py
.venv-macos/bin/python -m tools.check_macos_artifact
```

The verifier checks version/target/architecture and the DMG SHA-256, mounts the
image read-only, verifies its app, copies it into a temporary Applications directory
and detaches the image. It then runs that copy, with a fresh temporary home, through
both the dependency self-check and a synthetic profile lifecycle:

- First start creates a profile and renders the locked page without a GUI/network.
- A historical list-only encrypted vault is read and saved with DNS data.
- A separate process verifies that the key, credentials and active vault survive.
- The real authenticated/CSRF-protected `/restore_backup` rejects corrupt input, then
  restores a valid encrypted backup into a new file while retaining the original.
- Another process verifies the restored data and persisted selection.

The profile test command refuses a regular HOME or a non-frozen executable. It only
runs with a marker in a disposable `vsm-install-*` directory. CI retains JSON evidence
for 10 days; synthetic vaults/keys and binaries are not uploaded. This covers the
working encrypted inventory restore route added in 5.0.8. It does not
exercise GUI interactions, Gatekeeper, notarization, or macOS 13 itself.
By default the report marks cross-version upgrade as `not_tested`.
Runner reference: [GitHub hosted runners](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job).

### Cross-version packaged upgrade (local)

Keep a trusted previous local DMG outside the build output before rebuilding. Then run:

```bash
.venv-macos/bin/python -m tools.check_macos_artifact --previous-dmg /absolute/path/previous-local.dmg
```

The previous app must support the guarded profile smoke command (5.0.7 or later)
and have a strictly lower version. This executes both binaries: the older app
creates and verifies a synthetic profile, then the verifier replaces its temporary
installed bundle with the current app. The new app verifies the retained key,
credentials, DNS and selection, restores a backup and verifies another restart.
Both images are detached before their apps execute. No installed application or
real user profile is modified. Use only a trusted DMG: this option executes its code;
an ad-hoc signature verifies integrity, not publisher identity.
The JSON report records `upgrade.status`, `from_version` and `to_version` only on
success. Ordinary CI without a previous DMG does not claim an upgrade test.
This does not establish compatibility with 4.x or test a GUI upgrade/Gatekeeper.
