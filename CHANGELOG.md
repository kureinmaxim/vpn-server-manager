# Changelog

All notable changes to VPN Server Manager. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [5.0.4] - 2026-10-27

### Fixed
- Apple Silicon macOS builds can use an isolated CPython 3.13.12 runtime and hash-locked runtime/build dependencies instead of inheriting the host's Homebrew deployment target.
- The default macOS target is 13.0. A dependency requiring a newer OS fails before signing; the plist distinguishes the selected target from the measured binary minimum in the manifest.
- A packaged dependency/cryptography self-check must pass before DMG creation. It does not access user profiles or remote servers.
- Intel builds through the isolated launcher fail explicitly: current cryptography releases no longer publish macOS x86_64 wheels. No automatic downgrade is applied. GUI validation on macOS 13 and public notarized distribution remain pending.

## [5.0.3] - 2026-10-27

### Fixed
- macOS builds no longer overwrite the installed user's configuration. Version metadata comes only from the tracked template; build outputs and caches use dedicated local directories.
- Final plist changes precede ad-hoc signing and strict signature verification. Packaging preserves bundle symlinks, verifies the staged app and checks the DMG; failures stop the build.
- Architecture and minimum binary deployment target are derived from collected Mach-O files. Local image names include version/architecture, and a JSON manifest records signing status and SHA-256. These artifacts are explicitly not notarized public releases.

## [5.0.2] - 2026-10-27

### Fixed
- SSH host-key errors distinguish unknown, changed and unreadable trust records. Messages show only the endpoint and public SHA256 fingerprints, with independent-verification guidance. Malformed or unsupported `known_hosts` entries fail closed.
- Successful changes to a card's SSH credentials or addresses close its existing connections, including dedicated operations. In-flight connections cannot return to the pool after revocation; unrelated card edits retain connections.
- Pooled connections recheck credential/key-file content and local trust on acquisition. Changes to `known_hosts` revoke existing sessions on the next SSH access. No automatic trust acceptance or remote-operation retry is added.

## [5.0.1] - 2026-10-27

### Fixed
- **Key rotation:** write and verify a new encrypted vault before switching the profile. A private recovery journal restores the old environment/configuration after an interrupted switch; a committed switch retains the new generation. Startup recovers before registering data services.
- A shared profile lock and generation checks prevent stale application instances from writing after key rotation. Missing active vaults, mismatched profile keys and undecryptable inner credentials abort rotation instead of creating empty or mixed-key data.
- Recovery state is excluded from Git and rejected by the packaging privacy check. Tests include fault injection at each commit stage, interrupted rollback and abrupt termination of a separate process.

## [5.0.0] - 2026-10-26

### Changed
- **Security foundation (major-version branch):** all SSH connections now require a trusted host key in the local OpenSSH `known_hosts`. Verify a new host fingerprint independently before connecting; changed or unknown keys are rejected, including monitoring installation.
- All modifying HTTP requests require a session CSRF token and same-origin checks. Monitoring install/uninstall use POST streams without automatic retries; HTTP GET no longer closes the app. Local hosts are restricted to loopback/localhost unless explicitly configured.
- **Bots:** checks read service/container metadata and process names only. Token discovery, Telegram getMe and command-line/plist scans are disabled, including profiles with previously enabled settings. Legacy catalog fields remain preserved but are not probed.

### Fixed
- Vault saves use a same-directory temporary file, fsync, atomic replacement and a previous encrypted snapshot (`.backup.enc`). Cross-process locking and snapshot revision checks reject stale changes instead of overwriting them. Unreadable, missing active or malformed vaults cannot silently become an empty inventory.
- Profile settings use atomic writes and reject stale versions or corrupt input; invalid PIN configuration no longer falls back to a default. Legacy form login uses the configured PIN and shares a server-side attempt limiter with AJAX login and PIN changes.
- Removed authentication bodies, session dumps and partial encryption keys from diagnostic logging. Copied SSH commands quote every shell argument and accurately describe possible password prompts.

### Notes
- This is the start of the 5.0 line, not a signed macOS release. See [migration and verification notes](docs/SECURITY_FOUNDATION_5.0_ru.md) for scope, recovery and remaining release gates.

## [4.16.0] - 2026-10-26

### Added
- A third theme, **Minecraft**, in the theme menu next to Light and Dark: a dirt-brown palette with green accents, square corners, bevelled 2 px borders and hard shadows, as in ApiHA. It is a separate skin on top of the dark theme (`data-skin="minecraft"`) with its own stylesheet, `static/css/theme_minecraft.css`; the Light and Dark themes are unchanged. The choice is remembered like the other themes.

## [4.15.11] - 2026-10-26

### Fixed
- **Settings → Home page buttons** no longer says "saved" when `config.json` cannot be written (for example, no write access to the app folder). It now shows an error with the file path, and the buttons keep their previous state.

## [4.15.10] - 2026-10-25

### Added
- The **Tracked bots** page explains that bots which only send messages and keep no process (timers, Uptime Kuma notifications, containers with TELEGRAM_* variables) don't need a catalog entry: the Bots window finds them by bot number or @username and shows them at the top.

### Changed
- README screenshots of the server board, Settings, the server form and About show the current interface, with demo servers on documentation addresses.

## [4.15.9] - 2026-10-25

### Added
- Every inner page has the same navigation: a **Back** button to the page it belongs to, and the section trail. For example, Tracked bots shows «Back · Server list / Settings / Tracked bots», and Back returns to Settings rather than to the server list. Back follows the trail, not the browser history, because the app window has no browser buttons. Pages that had no way back now have one: Settings, Tracked bots and projects, Hint management, About, Help, Add server, Edit server, Monitoring, DNS / Chatmail, Server management, Disk usage, TelegramOnly cleanup and archives. Net Tools, Cheatsheet and DNS use the same component instead of their own links.

### Changed
- Tracked bots and Tracked projects are cards, one per entry, with labelled fields instead of a cramped table. List fields grow with their text, so long lists of services and containers are fully visible instead of cut at the edge of the field.

## [4.15.8] - 2026-10-25

### Changed
- The **Settings** page has the same look as the DNS and Monitoring pages. A header with section chips leads to Interface, Data and Security. The home page buttons are tiles with switches and links to their lists. The data file, import, key and PIN are uniform panels with consistent buttons: the main action is solid, key and full exports are amber, and «Detach file» is red. The page works in light and dark themes and at phone width. The export window is a real dialog and warns that the key and PIN unlock every server password.
- The PIN panel now changes the PIN, through the same check as the lock screen, instead of «Reset PIN lock». The lock only applies on the lock screen, which you must pass before you can open Settings.

### Fixed
- «Generate» next to the new encryption key called a missing address and did nothing. The Fernet key is now generated in the browser.
- Duplicate scripts at the bottom of the page replaced the real handlers. Changing the key skipped the check that both fields match (the server still checked), and export downloaded right away without the info window.

## [4.15.7] - 2026-10-25

### Added
- Settings → **Home page buttons**: switches for **DNS**, **Server load**, **Projects** and **Bots**. A tool that is off disappears from the home page and its window is not loaded. With Projects off, the «My projects» block also leaves the monitoring page and the server status window. Saved lists and data are kept. IP Test, DNS Test and Net Tools are always shown.

### Changed
- In a new installation **Projects** and **Bots** are off, because they come with catalogs for the author's own projects and Telegram bots. DNS and Server load stay on. Saving the language or zoom no longer drops other UI settings.

## [4.15.6] - 2026-10-25

### Added
- The Monitoring page shows the exchange with the server while it loads. Each request (connection, CPU and memory, tools, network, firewall, services, HA stack, web panels, security) is a step that turns from queued to running to done with its time, or to failed with the reason in the tooltip. A bar, a «N of 9» counter, elapsed time, data received and an estimate of the time left are based on this server's previous load. After loading, the panel folds into one line, «Data received in 27 s · updated N s ago». It pulses and names what it is refreshing during background polls, and the details reopen with one click.

### Changed
- The other checks start at most 4 s after the CPU sample instead of waiting for the whole history request, about 3 s sooner on slow servers.

### Fixed
- A single failed request (the tools check) no longer shows the «Cannot connect over SSH, timeout» banner. The failed step is shown in the exchange panel and retried on the next poll.

## [4.15.5] - 2026-10-25

### Fixed
- **Analyse the situation** told you to turn off `PasswordAuthentication` because «the app logs in with the card's SSH key», even on cards with only a password. Following that advice would cut the app off from the server. The loop that reads `sshd -T` overwrote the key argument, so the app always looked as if it used a key. Password-only cards now get the safe advice: add a key to the card and check that it works first.

## [4.15.4] - 2026-10-25

### Fixed
- **System services**, **VPN / Proxy services** and **TelegramOnly stack** on the Monitoring page could stay on «Loading...» for good. Each unit was checked with 2–5 separate SSH commands, about 60 per server. On a slow 1-vCPU VPS that took almost two minutes, the 30-second poll overlapped with itself, and SSH channels stopped opening («Timeout opening channel»). All units are now read with one `systemctl show` command, so the check takes seconds instead of about 110 s on srv015890413. If the request still fails, the lists say so and retry instead of showing «Loading...».

## [4.15.3] - 2026-10-25

### Fixed
- **Analyse the situation** on the Monitoring page answered «Rate limit exceeded» and showed an empty LLM prompt. All monitoring requests shared a limit of 10 per minute per server, and the page's own polling already used about that much. Now the shared limit is 30 per minute and the analysis has its own limit, so polling no longer blocks the button. The rate-limit message is translated, and the LLM prompt block with its Copy button is hidden when there is no prompt.

## [4.15.2] - 2026-10-25

### Changed
- Monitoring page: the priority strip is now one row of status chips in the same style as the Bots window: firewall (and whether the SSH port is allowed), failed SSH logins with the most frequent IPs in the tooltip, Fail2Ban bans, failed units by name, journal errors, security updates and missing tools. Green means fine, grey is information, yellow needs attention and red is a problem. The security brief button appears only when something needs attention.
- The memory sparkline uses an absolute 0–100 % scale, and network bars show KB/s or MB/s with a 1 MB/s floor, so a quiet link no longer looks full.
- «System update» shows when the package lists were last refreshed (today or N days ago) and when packages were last upgraded.
- The UFW check warns only when UFW is on and the SSH port has no ALLOW rule. The tools alert no longer opens by itself when all tools are installed.

### Fixed
- On servers where the SSH user is root without sudo, every `sudo` check failed silently: UFW looked inactive and SSH failures, bans and updates showed 0. Commands now run without sudo for root and with `sudo -n` otherwise.
- Failed SSH logins were counted twice (sshd and PAM lines) and included the check's own command. Now only sshd «Failed …» lines count, and the journal error count leaves sshd out.
- CPU showed 100 % on 1-vCPU servers because the monitoring probes measured themselves, «top now» was a lifetime average, and hypervisor steal counted as load. CPU is now a 1-second /proc/stat sample without the app's own processes, steal is shown separately, and «top now» is the same second.
- The CPU history jumped between 0 and 100 when the server's cron script was an old version that parsed `top`. The page detects it and offers **Update history script**, which replaces only `/usr/local/bin/monitoring/update-metrics-history.sh` over a verified (known_hosts) SSH connection. The new script also leaves steal out.
- The «Fix» button in the tools alert was translated as «Save».

## [4.15.1] - 2026-10-25

### Changed
- The Bots window is easier to scan. Sending-only bots come first, one card per bot (@username and ID), with their places in aligned columns: node, where, schedule, last run and result. Bots with a process are one table across all nodes (bot, node, state, uptime, memory, components). The components of a bot fold into one line, and its tasks show underneath. Nodes are a row of chips with their state, and node notes appear in the chip tooltip. Nodes without bots, helper jobs, suspects and node notes are folded at the bottom. SSH errors stay visible under the chips.

## [4.15.0] - 2026-10-25

### Added
- Bots window: a **Sending-only bots (no process)** section. These bots have a token in settings while a timer, Uptime Kuma or another program sends the messages. The window finds systemd timers whose script mentions `api.telegram.org` or `sendMessage`, or whose EnvironmentFile has `TELEGRAM_BOT_TOKEN`, Uptime Kuma Telegram notifications, and containers or TOS Docker stacks with `TELEGRAM_*` / `*BOT_TOKEN` variables (names only). Each bot is shown by its numeric ID, the part of the token before the colon, which the server cuts out. Optionally getMe runs on the server to show the bot's @username, and a setting turns this off. The same ID in several places is one bot. Each place shows the schedule, the next and last run with its result, or whether the Kuma notification is on.
- Bots on macOS: the catalog has **Command line** fragments (matched in `/bin/ps` as whole words) and **Bot tasks** (shown as rows under the bot). Defaults add Hermes (`hermes gateway run`, with the lesson-report tasks) and «Проверка уроков». Only the pid, user, uptime and memory of a match leave the node, never the command line. A process started by launchd is marked as a launchd agent, with its label when the plist is readable.
- The Bots window also checks the computer the app runs on, locally and without SSH.

### Changed
- «bot» marks a suspect only as a word or a name prefix, so certbot and robot are no longer flagged.
- The bots check runs under `/bin/sh` on every node, whatever the login shell (zsh on macOS), and skips its own shell and that shell's ancestors when matching processes.

### Security
- Tokens and chat_id never leave the node: the ID is cut on the server, getMe gets the token through curl's stdin (not argv), and sendMessage is never called. Anything that looks like a token in the output is masked again as `bot***`.

## [4.14.3] - 2026-10-24

### Fixed
- The SSH command on a card includes the saved key, for example `ssh -i ~/.ssh/id_ed25519 -p 9222 mxm@100.64.0.6`, and says that no password is needed. Before, the copied command asked for a password even though the app itself logs in with the key. A key pasted as text is not a file, so for that case the card explains how to add `-i`.

## [4.14.2] - 2026-10-24

### Fixed
- In the server form, the dropdown arrow no longer covers the text of narrow lists such as the address type (Mesh / LAN).
- The English and Chinese interface no longer shows Russian text in the server form (SSH password hints, “Root only”, clearing the panel and hoster), on the PIN screen and in the monitoring summary.

## [4.14.1] - 2026-10-24

### Added
- A card can have **extra addresses** (mesh, LAN, direct) next to the main IP. SSH tries the main IP first, then the extra addresses in order. The first one that answers on the card's SSH port is used and remembered until the app restarts, and every SSH feature (status, monitoring, load, projects, bots, reset, service control) uses it. For example, a NAS that accepts SSH only from the home LAN is still reached at home through its LAN address. Mesh marks and Server load also match the card to Tailscale peers by any of its addresses.

### Changed
- For **NAS** and **PC** cards the server form hides what only a rented VPS needs: hosting provider, payment, hoster account, receipts, and the DNS-leak and streaming checks. The card hides them too. The values are kept, so switching the node type back to VPS loses nothing.
- When a card already has an SSH key, the form shows “SSH key saved” in green and names the field “Replace SSH key”. An empty field reads as “keep the saved key” instead of looking as if the key was lost.

### Fixed
- English hints in the server form: the IP field said “For example, Ubuntu 22.04”, and the name and provider fields only said “for example”. About 20 other wrong English translations were also corrected, for example “Stop NGINX” shown as “Install package” and “PIN management” shown as “Hint Management”.
- Chinese translations of command-line messages lost their `{…}` placeholders, so a message could fail when it was shown. A test now checks that examples and placeholders survive translation.

## [4.14.0] - 2026-10-24

### Added
- **Bots** button on the main screen, next to Projects. It opens a summary of the Telegram bots on every active card: running, stopped, failed or restarting, since when, restart count, memory, and the result of an optional local health check. Nodes are checked in parallel, each with its own progress and error, and **Refresh** runs the check again.
- The bot list is edited under **Settings → Bots** (`/settings/bots`). Defaults: TelegramOnly with a health check on `127.0.0.1:8000/health`, BotCriptoM, telegram-helper-lite, plus the timer jobs TelegramOnly maintenance and Weekly monitoring report.
- Timer (oneshot) jobs, including oneshot services inside a bot, are shown in a separate **Helper jobs** block with the time and result of the last run. They do not count towards a bot's state.
- Services and containers with *bot* or *telegram* in their name that are not in the list are shown as **Looks like a bot**.
- Server cards have a **Node type**: VPS, NAS or PC. NAS and PC cards show no payment and stay out of **Server load**, while Projects and Bots still check them. A TerraMaster NAS without Docker access shows “Containers unavailable (TOS)” instead of an error, and Docker installed under `/Volume*/@apps/DockerEngine` is found.
- Tailscale peers of this PC that have no card are listed in the Bots window. They are not checked.

### Security
- The Bots check is read-only. It only runs `systemctl show` with a fixed property list, `systemctl list-units` filtered by name, `docker ps`/`docker inspect` with fixed fields, `pgrep -x`, and `curl` on `127.0.0.1`. The node checks the health reply itself, and only ok/fail leaves it. Environment, env files, container `Config.Env`, `/proc/*/environ`, bot configs and logs are never read. Bot names, health URLs and expected words are validated before they reach the shell.
## [4.13.5] - 2026-10-23

### Changed
- **Server load** names the reason when SSH to a server fails instead of one generic message: wrong login or password, closed or refusing SSH port, address not found, timeout, or an SSH session that did not open (fail2ban or connection limits). The text never includes remote error details.
- When SSH to a server is unavailable, **Server load** still matches it to your Tailscale network by server name, as the server cards do, and says so, instead of showing *Mesh unknown*.

## [4.13.4] - 2026-10-23

### Added
- **Server cards** show a purple globe when your own **AdGuard Home** DNS server is found; click it to open its diagnostics. The colour follows the service state, as for the Chatmail envelope.
- A tooltip on **Peer home DERP** in **Server load** and on the DERP mark of a server card explains what a home DERP is and that it is neither the path of your traffic nor proof of relaying. A relay from your own DERP map is marked *(custom)* in **Server load**.
- [DERP_GUIDE.md](DERP_GUIDE.md) and [ADGUARD.md](ADGUARD.md): guides on reading the DERP information, checking your own relay, and opening, checking and using your own AdGuard Home. Examples use placeholder names and documentation IP ranges only.

## [4.13.3] - 2026-10-23

### Fixed
- **Own DNS server → Panel**: when the AdGuard panel port cannot be detected (AdGuard installed as a service), the SSH tunnel command no longer contains the literal `PORT`. A port field (3000 by default) fills it in, and the copy button copies the finished command.

## [4.13.2] - 2026-10-22

### Added
- Compact and expanded **server cards** show an orange envelope when **Chatmail relay** is found; click it to open Chatmail diagnostics.
- **About** links to the GitHub repository.

### Changed
- Compact **server card** headers shrink the name first, so mesh and **Rust File Manager** icons stay visible.
- The **logout** icon sits at the right end of the top bar, after zoom, language and theme.
- README screenshots and the “latest patch” blurb match 4.13.x: no Help menu, role icons on cards, GitHub link on About.

## [4.13.1] - 2026-10-22

### Changed
- **Cheatsheet** opens one section when you click a card, same as Network tools. The index is only the card grid.
- Opened **Cheatsheet** and **Network tools** pages use a tighter type and spacing.

## [4.13.0] - 2026-10-22

### Added
- **Server cards** show small icons from this PC’s Tailscale mesh: in the mesh, the selected exit node, the coordinator, and the peer’s home DERP. A rust-coloured folder appears where **Rust File Manager** is installed; click it to open monitoring. Hover for the name. Mesh icons stay hidden if Tailscale is not connected.
- **Projects** lists **Own DERP** next to Chatmail and AdGuard when Headscale has an embedded DERP server enabled.

### Changed
- **DNS** page order is DNS providers, then Domains, then Own DNS server.
- Compact **server cards** no longer show the orange DNS-record cloud. The expanded card still has the cloud, the record list and the move action; the **DNS** page keeps the full domain panel.
- The **Help** menu is gone from the top bar. Hint editing is under **Settings**.
- **Cheatsheet** uses the same layout as Network tools: breadcrumb, card grid, and a copy button above each command.

## [4.12.15] - 2026-10-21

### Added
- **Own DNS** cards are stored in the same encrypted file as domains: add a VPS by hand, or let **Refresh** write what SSH finds. If the server is unreachable, the last saved card and setup steps stay on the page. The panel password and DoH URL are still not stored.
- **AdGuard Home / DNS** and **Chatmail relay** are in the editable tracked-projects list (they already appeared in the Projects window). A saved copy of the previous default list picks them up without wiping other custom projects.

## [4.12.13] - 2026-10-21

### Added
- **DNS** shows your own AdGuard Home server when one is found on an active server: whether clients can reach it by DoH only, by a Tailscale address or on an open port 53, plus setup steps for the panel, browser, macOS, Windows, Linux, Android, iPhone, OpenWrt (https-dns-proxy, SSClash, Podkop, Forkop or Zapret — one stack at a time) and the whole tailnet. The panel password is not shown; a DoH address typed on the page stays in that tab only.

## [4.12.12] - 2026-10-21

### Added
- **Server load** shows the own DNS server (AdGuard Home) and the Chatmail relay for Delta Chat on the servers that run them. Each role has its own colour (purple for DNS, orange for Chatmail), a dot for the service state, and the result and time of the last functional check from the **Status** button; click the badge to open its diagnostics. Roles are discovered read-only over SSH, in parallel with the DERP probe.

## [4.12.11] - 2026-10-13

### Fixed
- A DERP measurement taken right after switching exit nodes, while the new route is not ready yet, can return no latencies. Such a result is now kept for 15 seconds instead of 3 minutes, and **Server load** says to click **Refresh** in a few seconds instead of showing a 3-minute cache note.

### Changed
- **Server List → Net Tools** now matches the rest of the app: smaller tool cards and headings, compact port buttons, and the run button keeps its icon while a check is running.

## [4.12.10] - 2026-10-13

### Added
- Hovering over the DERP summary and region latencies in **Server load** explains what each value is. A region latency is the round trip from this PC to that DERP server; with an exit node selected, the tooltip shows the route through the exit node.

### Fixed
- The DERP measurement is repeated as soon as the exit node, the home DERP region or the Tailscale connection state changes. Before, the previous result stayed cached for up to 3 minutes, so switching exit nodes appeared to have no effect on latencies.

## [4.12.9] - 2026-10-12

### Changed
- **Projects** lists the components found under each server badge, marking processes and their count, and names the processes it checks. A process with the same name as a running service, such as `rnsd`, is no longer counted twice.

## [4.12.8] - 2026-10-12

### Added
- Tracked projects can include **processes**: programs started without a systemd service or container, such as `rnsd` run by hand in a terminal. Only the process name (as shown by `ps`, up to 15 characters) and the number of matching processes are read. Reticulum checks `rnsd` and `lxmd` by default.

## [4.12.7] - 2026-10-12

### Added
- The list of tracked projects is editable under **Projects → Edit list**. For each project, enter its systemd service and Docker container names. Each name is checked against an allowlist of characters before it is used in the read-only server check. The list is stored in the user profile, and **Restore default list** brings back the built-in list.

### Changed
- The default list now covers BotCriptoM, Rust File Manager, UGCTL, Reticulum, Dockhand, and Headscale with Headplane. ApiAigRPC, ApiNgRPC, ApiXgRPC, TelegramHelper and PDF3MD are no longer checked.
- Reticulum is found however it runs:
  - as the HA bridge, either the `ha-reticulum-bridge` service with the `ha-rns-watchdog.timer` timer or the `ha_rns_bridge` container;
  - as the `rnsd` or `lxmd` daemon;
  - as the `reticulumpn` propagation-node container. Services can be tracked by their `.timer` or `.socket` unit.
- **Projects** shows why a server could not be checked.

## [4.12.6] - 2026-10-12

### Added
- **Projects** next to **Server load** shows where your own projects run across active servers: BotCriptoM, Rust File Manager, UGCTL, ApiAigRPC, ApiNgRPC, ApiXgRPC, TelegramHelper and PDF3MD (TelegramOnly has its own section). Each server badge shows the project state and how many of its services and containers are running, and opens that server's monitoring.

### Changed
- Server Status and Monitoring show **My projects** instead of the Rust File Manager block: every found project with its systemd services (CPU, memory, tasks) and Docker containers. The check reads only fixed systemd properties and container names and states.
- Translated remaining Monitoring and Status labels for English and Chinese.

## [4.12.5] - 2026-10-12

### Added
- Domains can take their registrar, registration date and expiry date from the public RDAP record of the registry. **From RDAP** in the domain form fills the fields for review before saving; the **RDAP** button in the domain list updates the domain and lists the changed fields. The registrar website fills the account field only when it is empty. Lookups go through the existing WHOIS/RDAP check (HTTPS and public addresses only).

### Changed
- The domain list shows DNS records as "N main" and "N more service" instead of "N / M"; the column header explains the two groups.

### Fixed
- RDAP lookups for `.me` domains, whose registry is missing from the IANA bootstrap used by rdap.org, go to the Identity Digital RDAP server directly. A registrar's RDAP server link is no longer taken for its website.

## [4.12.4] - 2026-10-12

### Changed
- Rust File Manager and its optional internal bridge appear in Status and Monitoring, with systemd state, sampled CPU usage, service memory and task count. Unavailable counters remain unknown; checks do not read credentials or alter services.
- Monitoring uses the application's light/dark theme, with persistent CPU, memory and network readings, compact section switching, and expandable terminal commands. Only the selected section is shown, reducing vertical scrolling.
- Server Status keeps resource readings visible and groups processes, interfaces, Docker containers and service details into keyboard-accessible disclosures. CPU usage now includes a numeric percentage.
- Improved responsive layouts and English/Chinese labels. PNG export expands diagnostic sections in its capture copy.

### Fixed
- Monitoring's stylesheet was declared in an unused template block and never loaded. It is now included in the rendered page, with styles scoped to monitoring and its uninstall dialog.

## [4.12.3] - 2026-10-10

### Fixed
- Disk usage, Cleanup archives, Reset and Service control failed with the generic SSH message when `~/.ssh/known_hosts` contained a line paramiko cannot parse (an `@cert-authority`/`@revoked` marker or a damaged entry): paramiko stops reading the whole file with `InvalidHostKey`, which is not an `SSHException`, so the failure was not recognized. Such lines are now skipped and the rest of the file is read line by line; host key checking stays strict.
- When a failure still has no known cause, the message ends with the exception class, for example `(EOFError)`, so the cause can be found without logs. The exception text is still not shown.

## [4.12.2] - 2026-10-10

### Fixed
- Disk usage, Cleanup archives, Reset and Service control failed with the generic SSH message on servers whose login prints text (a banner or output from `~/.bashrc`/`~/.profile`): the text was read together with the script's JSON answer. The command now prints a marker first and only the output after it is parsed; text printed at login is ignored.
- The remaining failures after login are named too: an answer in an unexpected format (with the `ssh … true` check), a `python3` error (version older than 3.7), no data, or an SSH channel closed by the server. Operations that change the server still show "answer lost" for anything after the command may have started.

## [4.12.1] - 2026-10-10

### Fixed
- Disk usage, Cleanup archives, Reset and Service control showed only "Check SSH, known_hosts and root/sudo -n" on any failure. They now name the cause and the fix: the server key is not in `~/.ssh/known_hosts` (with the exact `ssh -p … user@ip` command to accept it), the key changed (with `ssh-keygen -R`), login failed, the server did not answer, `python3` is missing, or `sudo` asks for a password. Operations that change the server report only causes known to happen before any command ran; otherwise the previous "answer lost" text stays. Exception texts and server stderr are still never shown; the log records only the cause code.
- These operations now log in exactly like monitoring: with the password and/or key from the card. `~/.ssh` keys and ssh-agent are tried only when the card has neither, so agent keys no longer use up `MaxAuthTries` before the password.

### Documentation
- README (SSH login) and `docs/SECURITY_BEST_PRACTICES_ru.md`: these pages require the server key in `~/.ssh/known_hosts`; how to add it.

## [4.12.0] - 2026-10-10

### Added
- SSH key login. The server card (SSH access) accepts an SSH key: a path to the private key on this computer (`~/.ssh/id_ed25519`) or the pasted key, with an optional passphrase. Ed25519, ECDSA and RSA keys are supported, including encrypted ones. The key is checked on save; an unreadable key is not saved, the rest of the card is, and a warning explains why. The key and passphrase are stored encrypted like passwords; the card shows only the fingerprint (`ssh-ed25519 SHA256:…`) and the path, never the key. The trash button removes it.
- Every SSH connection uses the key from the card: status, monitoring, load overview and DERP, security events and brief, monitoring install/uninstall, service control and reset. If both a key and a password are set, the key is tried first, then the password. Servers without a key work exactly as before.

### Changed
- Security brief: the advice to turn off `PasswordAuthentication` (and root login by password) now warns that the app still logs in with a password and will lose access until an SSH key is set in the card. When the card already uses a key, it says that password login can be turned off.
- Change of the main key and import from another data file re-encrypt the SSH key and its passphrase together with passwords.

### Documentation
- README: new section **SSH login: password or key** — what the card accepts, how the app chooses between key and password, switching a server to key-only login, and what backups contain for keys saved as a path.
- `docs/SECURITY_BEST_PRACTICES_ru.md`: how the key is stored and the safe order for switching a server to key-only login; the monitoring guide mentions the key option.

## [4.11.3] - 2026-10-09

### Added
- DNS → **Import zone file** has a **Replace records to match the file** mode. For a domain that is already in the list, records that are not in the file are deleted, so the card matches the provider after records were removed there (for example, after cleaning up leftovers of an old hosting). Matching records keep their id, group and note; only the Cloudflare proxy flag is refreshed. The domain's provider, registrar, dates and notes are not touched. Domains that are not in the list yet are created as with a normal import.
- Safety: if a file has unreadable lines or no records, replacement for that domain is cancelled and its records stay unchanged, so an incomplete export cannot wipe live records. RU/EN/ZH labels and messages.

### Documentation
- New `docs/DNS_CARD_ru.md`: what the DNS card stores, both zone import modes, the replace guard, and when a Cloudflare record must stay **DNS only** (private and Tailscale addresses, Headscale, VPN protocols, SSH, mail, certbot sites), including the dashboard banner "Proxying is required for most security and performance features". Linked from README and the docs index.

## [4.11.2] - 2026-10-08

### Fixed
- macOS: the server load overview showed "Mesh unknown" and DERP diagnostics were unavailable when the app was launched from Finder/Dock. The bundle receives a minimal PATH without `/usr/local/bin`, so the Tailscale CLI is now also looked up in `/usr/local/bin`, `/opt/homebrew/bin` and `/Applications/Tailscale.app`.

## [4.11.1] - 2026-10-08

### Added
- DERP overview with the PC's home region, UDP status, netcheck preferred region, five lowest measured latencies and all custom regions. Netcheck runs separately from load metrics with a 12-second budget and a three-minute in-memory cache; exit-node measurements show a warning.
- Read-only SSH diagnostics for Headscale's embedded DERP, local HTTPS probe, STUN listener and prospective DERP hosts (public interface IPv4 and TCP 443/UDP 3478 occupancy). Only allowlisted configuration fields are returned; missing permissions or unsupported YAML remain unknown.
- On-demand, bounded `tailscale ping` confirms the peer path. Empty `CurAddr` no longer implies relay use: idle peers show an unconfirmed path and their home DERP separately. A later direct pong supersedes the initial relay pong.

### Changed
- Removed the per-row Checked column; completion time appears beside the counters above the table. Added RU/EN/ZH labels for DERP diagnostics.

## [4.11.0] - 2026-10-08

### Added
- Server load overview now shows Tailscale membership relative to the application host, ordinary nodes, available exit nodes, the exit selected on the PC and offline peers. Public SSH addresses are matched using remote Tailscale node IDs.
- Displays the local network/PC and coordinator control hostname. Cards matching that hostname or its DNS addresses are marked as the control endpoint, with a reverse-proxy/NAT caveat. Unavailable local status and invisible peers remain explicit rather than being labelled as outside the network.
- Authenticated, PIN-protected read-only mesh endpoint; only selected fields are returned, without raw Tailscale preferences or keys. Includes RU/EN/ZH labels.

## [4.10.3] - 2026-10-05

### Added
- NaiveProxy port changes for the single shared-account mode generated by TelegramOnly. The manager JSON and live Caddyfile must agree on domain, port and credentials; `caddy validate` runs before replacement and service health is checked after restart.
- Strict parsing of the generated Caddyfile with private backups and rollback. Client creation/revocation is blocked because shared-account NaiveProxy has no independent client list.

### Limitations
- Complex hand-written Caddyfiles, multiple sites, Docker and external authentication remain read-only. The adapter supports `/etc/caddy-naive/Caddyfile` with a dedicated `caddy`, `caddy-naive` systemd command. No live VPS was modified.

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
