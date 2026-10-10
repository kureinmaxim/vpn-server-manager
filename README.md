# VPN Server Manager v4.12.1

<p align="center">
  <img src="static/VPSc.png" alt="VPN Server Manager" width="140">
</p>

<p align="center">
  <strong>Your servers, their health, and how they connect — in one desktop app.</strong><br>
  Encrypted inventory · SSH management · Tailscale &amp; DERP diagnostics
</p>

<p align="center">
  <a href="https://github.com/kureinmaxim/vpn-server-manager/releases"><img src="https://img.shields.io/github/v/release/kureinmaxim/vpn-server-manager?style=flat-square" alt="Latest release"></a>
  <a href="https://github.com/kureinmaxim/vpn-server-manager/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/kureinmaxim/vpn-server-manager/ci.yml?style=flat-square" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-0F766E?style=flat-square" alt="MIT License"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/python-3.13+-3776AB?style=flat-square" alt="Python 3.13+"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-1F2937?style=flat-square" alt="Windows, macOS, Linux">
</p>

<p align="center">
  <a href="https://github.com/kureinmaxim/vpn-server-manager/releases/latest"><strong>Download for Windows</strong></a>
  &nbsp; · &nbsp; <a href="#quick-start">Run from source</a>
  &nbsp; · &nbsp; <a href="docs/INDEX_ru.md">Russian documentation</a>
  &nbsp; · &nbsp; <a href="CHANGELOG.md">What's new</a>
</p>

VPN Server Manager keeps server logins, panel credentials, domains and provider details in an encrypted local vault. Compare server load, inspect services over SSH, and see which machines belong to the Tailscale network of the PC running the app. Open it as a native desktop window or in a browser; a Telegram bot is optional.

**Latest patch · 4.11.3:** DNS zone import can replace a domain's records to match a Cloudflare export, removing records deleted at the provider while keeping the domain's registrar, dates and notes. [Release notes →](https://github.com/kureinmaxim/vpn-server-manager/releases/tag/v4.11.3)

## See your fleet at a glance

Open **Server load** next to DNS to compare CPU, memory, disk space, load averages and network traffic across active servers. Filter by name or address and sort by the metric that matters.

<p align="center">
  <img src="docs/images/07-load-mesh-overview.jpg" alt="Server load overview with resource metrics, Tailscale membership, coordinator and exit-node roles, and DERP region latency" width="1100">
  <br><sub>v4.11.1 · English interface · demonstration servers and addresses</sub>
</p>

| What you want to know | Where to look |
|---|---|
| **Which server is under pressure?** | CPU, memory and disk meters; sortable load and traffic columns. |
| **Is it in this PC's mesh?** | The mesh column matches visible Tailscale peers and shows regular nodes, available exits and the exit selected on the PC. |
| **Where is the coordinator?** | The control endpoint is named above the table and marked on matching server cards. |
| **Which relay is closest?** | The DERP summary shows measured region latencies, highlights custom regions and warns when netcheck runs through an exit node. |

## Understand the connection, not just the status

An idle peer can have an empty direct address. Its home DERP region alone does **not** prove that traffic is being relayed. Click **Check path** to send up to three Tailscale pings and see the last confirmed direct or DERP path with its check time.

<p align="center">
  <img src="docs/images/08-derp-diagnostics.jpg" alt="Expanded custom DERP diagnostics showing the confirmed peer path, Headscale version, HTTPS probe, STUN listener and port availability" width="1000">
  <br><sub>Read-only diagnostics · demonstration data, no private infrastructure details</sub>
</p>

Expand **DERP and port availability** to inspect an existing Headscale relay or assess a possible relay host: embedded DERP configuration, local HTTPS probe, STUN listener, public interface IPv4 and port occupancy. A successful local probe does not establish internet reachability; firewall and NAT still matter. [How the checks work →](docs/README_MONITORING_ru.md#derp-в-обзоре-загрузки-4111)

## Keep everyday operations together

<p align="center">
  <img src="docs/images/03-server-board.png" alt="Server board — compact cards, drag to reorder, archive" width="900">
</p>

## What you get

| | |
|---|---|
| **Encrypted vault** | Fernet encryption for server data. Import / export full backups. Lose the key, lose the data — by design. |
| **Desktop or browser** | Native window on Windows, macOS, and Linux, or `python run.py` for web mode. |
| **PIN lock** | Quick lock on the local app so a shared machine is not an open notebook. |
| **SSH monitoring** | Logs in with a password or an SSH key from the server card. Live traffic, firewall, systemd services, Docker, security events, CPU/RAM history. Knows TelegramOnly, Reticulum, and web panels (Dockhand, Headplane) over an SSH tunnel. |
| **Server management** | Inspect Docker and systemd services, control their lifecycle, and use supported protocol settings and client operations. [Supported configurations and limits](CHANGELOG.md). |
| **DNS & network tools** | Keep domains, providers, renewal dates and records together. Import Cloudflare zone exports: add missing records, or replace them to match the file after a cleanup at the provider. Run network checks and use terminal examples, including DNS queries with `dig`. [DNS card guide (RU)](docs/DNS_CARD_ru.md). |
| **Mesh & DERP** | Local Tailscale membership, coordinator and exit roles, custom relay diagnostics and an explicit path check. No Tailscale configuration changes. |
| **Works offline** | The inventory stays usable without internet. Network-only actions disable themselves cleanly. |
| **Languages** | Russian, English, and Chinese. `.po` catalogs compile on first launch. |

<details>
<summary>More screenshots: PIN protection, server editing and settings</summary>

<p align="center">
  <img src="docs/images/01-pin-lock.png" alt="PIN lock screen" width="430">
  &nbsp;
  <img src="docs/images/02-pin-modal.png" alt="PIN login dialog" width="430">
</p>

<p align="center">
  <img src="docs/images/04-add-server.png" alt="Edit a server and its SSH connection details" width="720">
</p>

<p align="center">
  <img src="docs/images/05-settings.png" alt="Application settings, encryption and import or export" width="720">
</p>

</details>

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

The current [release](https://github.com/kureinmaxim/vpn-server-manager/releases/latest) includes a Windows installer and SHA256 checksum. macOS and Linux users can run from source; see [BUILD.md](BUILD.md) for packaging.

For the load overview, save working SSH credentials in each server card — a password, an SSH key or both (see [SSH login](#ssh-login-password-or-key)). Mesh and DERP diagnostics also require Tailscale on the **application host**. Remote DERP inspection uses existing Python 3 and standard Linux tools; unavailable dependencies are reported without installing anything.

## SSH login: password or key

Every server card has an **SSH access** block. The app logs in with what you save there:

| In the card | How the app logs in |
|---|---|
| Password only | With the password, as before |
| SSH key only | With the key; password login on the server can be turned off |
| Key and password | Key first; the password is used if the key is refused |

The **SSH key** field takes either:

- a path to a private key on the computer running the app, for example `~/.ssh/id_ed25519` (works on macOS, Linux and Windows);
- or the private key text itself (`-----BEGIN OPENSSH PRIVATE KEY-----` …).

Ed25519, ECDSA and RSA keys are supported, including keys protected with a passphrase (enter it in **Key passphrase**). The key is checked when the card is saved. If it cannot be read (no such file, unsupported format, wrong passphrase), the card is saved without the key and a warning explains why.

The key and its passphrase are encrypted like passwords. The card shows only the fingerprint (`ssh-ed25519 SHA256:…`) and the path, never the key; the trash button removes it. Everything that connects over SSH uses the key: status and monitoring, the load overview and DERP, security events and brief, monitoring install, service control and reset.

### Switch a server to key-only login

1. On the computer running the app, create a key if you do not have one: `ssh-keygen -t ed25519`.
2. Copy its public part to the server: `ssh-copy-id -p PORT root@SERVER_IP`.
3. Check the login without a password: `ssh -o PasswordAuthentication=no -p PORT root@SERVER_IP`.
4. In the server card set **SSH key** to `~/.ssh/id_ed25519`, save, and check that status and monitoring load.
5. Only then turn off password login on the server: `PasswordAuthentication no` (for root also `PermitRootLogin prohibit-password`), then reload sshd. Keep the current SSH session open and test the login from a second terminal.

Until the card has a key, the security brief warns that turning off password login would lock the app out of the server.

**Known host key.** Monitoring and the load overview accept the server's host key on first contact. Operations that change or inspect the server more deeply — **Reset**, **Service control**, **Disk usage** and **Cleanup archives** — require the key to be in `~/.ssh/known_hosts` of the user running the app, so a replaced server cannot receive commands. Connect once from a terminal on the same computer (`ssh -p PORT root@SERVER_IP`) and accept the key. If one of these pages fails, it says why: unknown or changed host key, failed login, no answer, missing `python3` or `sudo` asking for a password.

A key saved as a **path** is read from that file on every connection. Backups contain the path, not the key file: on another computer put the key at the same path, or paste the key text into the card. A pasted key travels inside the encrypted data file.

Details in Russian: [docs/SECURITY_BEST_PRACTICES_ru.md](docs/SECURITY_BEST_PRACTICES_ru.md#вход-по-ssh-ключу).

## Backup and restore

Servers (with their passwords) and the DNS card (providers, domains, records) are stored in **one encrypted `.enc` file**. It can only be decrypted with `SECRET_KEY` from `.env`, so a backup is always **data file + key**.

**Back up:** Settings → **Full export** creates `vpn_servers_backup_<date>.zip` in Downloads:

| File | Contents |
|---|---|
| `servers_<date>.enc` | All servers and the whole DNS card |
| `SECRET_KEY.env` | The key for that `.enc` file |
| `PIN.txt` | Login PIN of the source install (a reminder; the PIN is per install and is not restored) |
| `uploads/` | Server icons |

The archive holds data, key and PIN together: anyone with it can read every password. Keep it in a password manager or on an encrypted drive, never in chats or git.

SSH keys saved in cards as a file path are not copied into the archive — only the path is. Pasted keys are included, encrypted. See [SSH login](#ssh-login-password-or-key).

**Restore**, depending on the target computer:

- **Fresh install (or full replacement):** close the app, put `SECRET_KEY.env` into the app data folder as `.env`, copy `uploads/`, start the app, then Settings → **Import Data File** → `servers_<date>.enc` → **Import and Attach**.
- **The computer already has its own servers:** keep its `.env`. Settings → **Import servers from another installation** → choose `servers_<date>.enc`, paste the value after `SECRET_KEY=` → **Import and merge servers**. Duplicates (same name or IP) and existing domains are skipped; passwords are re-encrypted with the local key.

App data folder: macOS `~/Library/Application Support/VPNServerManager-Clean/`, Windows `%APPDATA%\VPNServerManager-Clean\`, Linux `~/.local/share/VPNServerManager-Clean/`.

Files with DNS data need version 4.6.0 or newer. Step-by-step guide with troubleshooting: [docs/BACKUP_RESTORE_ru.md](docs/BACKUP_RESTORE_ru.md) (Russian).

## Safety notes

- Default PIN in the template is `1234`. Change it before real use.
- Keep `.env` (`SECRET_KEY`) and encrypted exports off shared drives and out of git.
- There is no password recovery. A full export is the backup.
- Prefer SSH keys for servers: with a key in the card, password login can be turned off on the server without cutting off the app.

## Docs

- [Documentation index](docs/INDEX_ru.md) (Russian)
- [Build guide](BUILD.md) · [RU](BUILD_ru.md)
- [Terminal help](TERMINAL_HELP.md) · [RU](TERMINAL_HELP_ru.md)
- [Version management](VERSION_MANAGEMENT.md)
- [Release process](docs/release_guide_ru.md) (Russian)
- [Monitoring](docs/README_MONITORING_ru.md) (Russian)
- [Docker](docs/DOCKER_GUIDE_ru.md) (Russian)
- [Changelog](CHANGELOG.md)
- [Lessons](lessons/README.md) (Russian: app + Git)

Questions: [Discussions](https://github.com/kureinmaxim/vpn-server-manager/discussions). Bugs: [Issues](https://github.com/kureinmaxim/vpn-server-manager/issues).

## License

[MIT](LICENSE)
