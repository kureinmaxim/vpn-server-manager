# Changelog

All notable changes to VPN Server Manager. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [4.10.2] - 2026-10-05

### Added
- Hysteria2 port changes and userpass client creation/revocation for dedicated systemd services using `/etc/hysteria/config.yaml`. Shared-password installations support port changes without changing authentication mode.
- Restricted parser for TelegramOnly's mapping-only YAML and JSON. Ambiguous YAML, duplicate keys and unsupported authentication/configuration formats are rejected. TLS and obfuscation must agree with manager metadata; unrelated settings are retained. The updated file uses JSON syntax, which is also valid YAML; backups retain original bytes and permissions.
- Protects the default client and checks its consistency with the root password to prevent TelegramOnly from restoring revoked credentials.
- Hysteria2 plans explicitly explain that validation checks structure, not native startup. Service startup failure triggers rollback. Client names use lowercase ASCII letters, digits, hyphens and underscores.

### Limitations
- No native Hysteria dry-run is used. Complex YAML, ACME, external authentication, Docker and automatic migration from shared passwords remain unsupported. Verification uses local files and simulated services; live VPS validation remains outstanding.

## [4.10.1] - 2026-10-05

### Added
- VLESS/Reality TCP port changes and client creation/revocation for a dedicated Xray systemd service using `/usr/local/etc/xray/config.json`. Validates the candidate with Xray before writing, with private backups and rollback on restart failure.
- Checks UUIDs, flow, Reality private key, short IDs, SNI and manager/runtime agreement. Existing routing and fallbacks are preserved. Detected 3x-ui installations cannot be edited directly, even when the panel is stopped.
- Protects TelegramOnly's default client from revocation because the bot can recreate it from the root UUID. Updated Russian, English and Chinese messages.

### Limitations
- Requires one existing matching manager file and one VLESS/Reality inbound, a running dedicated systemd service and a stopped bot. Docker, multi-inbound configurations, Hysteria2 edits and standalone installers remain unsupported. Validation was performed with simulated services and local Linux files, not a live VPS.

## [4.10.0] - 2026-10-05

### Added
- TUIC and XHTTP port changes and client creation/revocation through SSH for existing dedicated sing-box systemd services. UUIDs and passwords are generated on the server; plans and operation responses contain no credentials.
- Protocol-specific checks compare client credentials, TLS settings, TUIC ALPN/congestion control and XHTTP transport settings before writing. Both configurations are backed up and validated; failed restarts trigger rollback.

### Changed
- The confirmation panel and settings refresh follow the selected protocol. Updated Russian, English and Chinese interface text.
- Linux filesystem verification covers all three editable protocols, including failed writes, restarts and recovery.

### Limitations
- Edits require a single running service, matching manager metadata and a stopped TelegramOnly bot. Docker, native TUIC and Xray configurations remain read-only. XHTTP requires a sing-box build that accepts its configuration; validation failures leave live files unchanged. These changes were tested locally with simulated services, not on live VPS instances.

## [4.9.2] - 2026-10-02

### Added
- AnyTLS port changes and client creation/revocation for a single running, dedicated sing-box systemd service. Changes require matching manager/runtime configurations and a stopped TelegramOnly bot; plans are session-bound and expire after five minutes.
- Private backups, sing-box validation, atomic file replacement and rollback on failed service restart. Interrupted or unsuccessful recovery blocks further edits pending SSH recovery.
- Profile export for VLESS/Reality TCP, Hysteria2, NaiveProxy and Mieru, in addition to AnyTLS, TUIC, XHTTP and MTProto.

### Changed
- Server management uses a compact searchable service list with status filters and expandable actions. Protocol settings and clients can be opened from a service row; English and Chinese translations are included.

### Limitations
- AnyTLS configuration changes currently support systemd only, not Docker, and require an existing manager configuration and dedicated `/etc/anytls/config.json`. Standalone installation, other protocol edits and Mesh/HA/TLS settings remain in development. Filesystem rollback was tested locally on Linux with a simulated service, not on a live VPS.

## [4.9.1] - 2026-09-30

### Fixed
- Importing a data file encrypted with another key no longer reports "0 servers imported" and switches to an unreadable file; it now shows the key error and keeps the current file.
- Merging servers from another installation skips duplicates by IP address again (the check read a non-existent `ip` field, so only names were compared).
- English and Chinese labels of **Full export** and **Import and merge servers** no longer read "Import and Export" / "Import and Attach".

### Documentation
- New step-by-step guide `docs/BACKUP_RESTORE_ru.md`, a *Backup and restore* section in README, rewritten in-app Help and the README inside the full-export archive: what the archive contains (servers + DNS + key + PIN + icons), restoring on a fresh install versus merging into existing data, where the data folder is, and that the PIN is per installation.
- Help no longer claims that importing from another installation replaces current data, or that the sign-in screen can import an archive (that button does not work yet).
- `VERSION_MANAGEMENT.md` matches `tools/update_version.py`: every synced file (including the bug-report form), how `bump` and `sync` set dates, and a release checklist. `update_version.py status` now also checks `.github/ISSUE_TEMPLATE/bug.yml`.

## [4.9.0] - 2026-09-30

### Added
- **Server control** page: systemd and Docker service lifecycle actions, a shared service catalog, read-only protocol inspection and client URI export — the first step of moving TelegramOnly management into the app.
- Stricter `.gitignore` for private files and `tools/check_public_files.py` to check that no private paths are tracked.

### Fixed
- `setup_windows.bat` no longer replaces `SECRET_KEY` in an existing `.env` on reinstall, which made all data files undecryptable; the key is regenerated only with `--force`.
- Importing external data when the current data file cannot be decrypted now reports that problem instead of a wrong external key.

## [4.8.0] - 2026-09-30

### Added
- **Import zone file** on the DNS page: upload one or more BIND zone files (Cloudflare DNS → Records → Export). Missing domains are created with the chosen DNS provider; only records not already present are added. Multi-string TXT values (DKIM), MX/SRV targets and Cloudflare proxy status are preserved; SOA and apex NS records are skipped.

## [4.7.0] - 2026-09-30

### Added
- DNS records are split into **main** and **service** groups. Mail, cPanel, domain-verification and SPF/DKIM/DMARC records (MX, TXT, SRV, underscore names, cPanel hosts) are service records and collapsed by default; any record can be moved between groups manually.
- Record tables sort by name, type or value; private and Tailscale/Headscale (100.64.0.0/10) addresses are marked.
- Server cards show an orange DNS badge and a **DNS records** section listing names that point to the server IP, including CNAMEs that follow them.
- **Move to another VPS** helper: choose the new server, see each record as old IP → new IP with copy buttons and the provider link, then update the selected records in the DNS card.
- Net Tools suggests only main records; the domain list shows main / total record counts.

## [4.6.1] - 2026-09-30

### Fixed
- Changing the master key failed since 4.0 (`DataManagerService` was not imported) after `.env` had already been overwritten, leaving the data file unreadable on the next start. The re-encrypted data file is now written first and `.env` is updated only after it succeeds.
- Key change now re-encrypts server SSH, panel and hoster credentials and DNS-provider credentials with the new key; previously they stayed encrypted with the old key.
- Key change aborts on an unreadable data file instead of writing an empty one.

### Added
- Key verification reports the number of DNS domains in the file.
- End-to-end tests for export, full archive, import, external merge, key verification and key change with DNS data.

## [4.6.0] - 2026-09-30

### Added
- **DNS** card (orange button beside Net Tools): DNS-provider accounts (Cloudflare, Namecheap, GoDaddy, Porkbun, REG.RU, Route 53 or custom) with encrypted login and password and an "Open dashboard" button; domains with registrar, registration and expiry dates, auto-renewal and expiry warnings; DNS records and subdomains.
- Net Tools offers saved domains and subdomains from the DNS card instead of typing them.
- DNS data is stored in the same encrypted data file as servers, so it is included in export, import, merge of external files and key change. Files without DNS data keep the previous list format.

## [4.5.1] - 2026-09-29

### Fixed
- Net Tools examples use `example.com` instead of a personal hostname, including the dig and PowerShell commands and documentation.

## [4.5.0] - 2026-09-29

### Fixed
- Windows installer builds no longer traverse or delete local virtual environments and logs. Python caches and development directories are excluded during packaging, avoiding access-denied errors in sandbox-created test environments.

### Added
- **Net Tools** beside DNS Test opens a translated Russian, English and Chinese catalogue with nine diagnostic cards, explanations, terminal commands and copy buttons.
- Built-in TCP port, DNS, Ping, TLS, WHOIS/RDAP, HTTP, IP location and public IP checks. Reverse IP opens Connected's external database. Sources and the machine used for each check are shown explicitly.
- PIN session and request-token protection, public-address validation, pinned connections, bounded output and concurrency, and timeouts for network diagnostics.

## [4.4.15] - 2026-09-26

### Added
- UI language and zoom are saved in the user profile (`config.json`) and restored on the next launch.

## [4.4.14] - 2026-09-25

### Added
- Server-card action to reset the TelegramOnly stack, with dedicated reset, archive, and disk-usage pages.
- Status link on the reset page; Status opens for the selected server after install and leaves only setup checked.

### Improved
- Compact server-card layout and a **Delete archive** control for finished cleanup archives.
- English and Chinese UI: the back link **Servers** is translated (`Серверы` / `服务器`).

## [4.4.11] - 2026-09-24

### Added
- **Check IP** stores the city on the server card when that card has no geolocation yet, and shows it in the header immediately. A city that already matches the current IP is left unchanged.

## [4.4.9] - 2026-09-23

### Improved
- Monitoring cards stay as tall as their content, and the attack IP list is no longer repeated under the counters.
- htop and btop install commands stay visible under the load meters, each with its own copy button.

## [4.4.8] - 2026-09-23

### Improved
- The LLM prompt on Monitoring is a full-width block, and CPU is shown once on the meter. The line under the meters uses a one-second `/proc/stat` sample plus load average, and offers a copyable command to install `htop` or `btop` when neither is present.

## [4.4.7] - 2026-09-23

### Improved
- Monitoring puts overload and attacks at the top of the page. When either is present, **Review the situation** builds a secret-free summary and a prompt that can be copied into an LLM.

## [4.4.6] - 2026-09-23

### Improved
- Monitoring shows CPU, memory, and network as compact meters next to the existing charts.
- Server Status lists the whole TelegramOnly stack, including transports, the bot, the HA services, and expected containers. Missing pieces stay visible with the install script that adds them.

## [4.4.5] - 2026-09-22

### Improved
- Edit form can clear a stored password, a panel or hoster login, or the whole panel and hoster block. **Root only** sets the SSH user to `root` and moves the reference root password into the login password.
- Double-click opens one server card full width: summary on the left, SSH and the other sections on the right. The other cards stay in a compact grid.
- The SSH copy button names the login (`ssh user@host`) and which password belongs to that command. A second button copies `ssh root@…` when the login user is not root and root SSH is allowed.

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
