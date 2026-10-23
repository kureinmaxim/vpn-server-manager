# AdGuard Home guide

How VPN Server Manager finds and checks your own **AdGuard Home** DNS server, how to open its panel safely, and how to point devices at it. All names, addresses and ports are examples (`dns.example.net`, `192.0.2.10`, `203.0.113.5`, SSH port `2222`). Replace them with your own and never publish your real ones.

## What the app does (and does not do)

The app **detects and checks**. It does not install or configure AdGuard Home.

- **Discovery** (read-only, over SSH): the systemd units `AdGuardHome`, `adguardhome` or `adguard-home`, or a Docker container whose *image* is AdGuard Home (the container name can be anything). Docker image tag, Compose service and published ports are shown when Docker reports them.
- **Where you see it**
  - **Server load**: a purple **Own DNS server** badge with a state dot and the last functional check.
  - **Server cards**: a purple globe icon next to the other marks; click it to open the diagnostics.
  - **Projects** and **Status → My projects**: the role *AdGuard Home / DNS* with its components.
  - **DNS → Own DNS server**: a card per VPS with step-by-step device setup.
- **What it never touches**: the panel password and the secret DoH address are not read, stored or exported. No DNS, firewall, Caddy or service changes are made.

Process detection is **not** a health check. Use the functional check below for that.

## Functional check

Open **Monitoring → DNS / Chatmail**, choose the **AdGuard** role, review the parameters and press **Run check**. It is a one-time check from the VPS through the existing SSH connection.

| Check | Default | Notes |
|---|---|---|
| DNS UDP and TCP | `127.0.0.1:5300` | Port is configurable. A truncated UDP answer is reported separately; TCP is shown independently. |
| Local DoH | `127.0.0.1:3001/dns-query` | AdGuard serves `/dns-query` on its web port when plain HTTP is used behind a reverse proxy. |
| Public DoH | URL read **on the VPS** from `/root/dns-doh-url` | TLS trust, name and expiry, HTTP 200, `application/dns-message` and the DNS content are verified. An HTML 200 or a redirect is not DoH. |

- The test query is an `A` record for `example.com`. For `NOERROR` an address must be in the answer; `SERVFAIL` and an empty answer are failures. Choose `NXDOMAIN` only for a name you know does not exist.
- The secret DoH URL stays on the VPS. It is not sent to the app, saved in cards or shown in errors. The SSH user needs read access to the file (no automatic sudo). A missing file means "not configured"; a permission error means "unavailable".
- Each result has a reason, time, duration and the source **VPS via SSH**. It is marked stale after five minutes. The last result is kept in memory until the app restarts.
- A green result from the VPS does not prove the server is reachable from your home PC. Use **Net Tools** on the computer for that.

## Open the admin panel (SSH tunnel)

The panel is AdGuard's **web page**, not the DNS port. Open it only through an SSH tunnel or Tailscale, never on the server's public IP.

On your computer (Windows 10/11 PowerShell, macOS Terminal or a Linux terminal; OpenSSH is built in) run this and **keep the window open** while the panel is in use:

```bash
ssh -N -o ExitOnForwardFailure=yes -p 2222 -L 127.0.0.1:13001:127.0.0.1:3001 root@203.0.113.5
```

Then open `http://127.0.0.1:13001` in the browser.

| Part | Meaning |
|---|---|
| `-p 2222` | The SSH port of the VPS (omit if it is 22). |
| `13001` | A free local port on your computer. If it is busy, use another one and open that port in the browser. |
| `3001` | The port of the AdGuard panel **on the VPS**. |
| `root@203.0.113.5` | Your SSH user and the VPS address. |

- After you type the password nothing is printed; for `ssh -N` that is normal. Stop the tunnel with Ctrl+C.
- If the app cannot detect the panel port (AdGuard installed as a service), the **Panel** tab shows a port field (3000 by default, the wizard default). Enter the port chosen in the setup wizard; the command updates as you type. To find it on the VPS: `ss -ltnp | grep -i adguard`.
- If the panel is already reachable on a Tailscale address, the app shows that direct link instead of a tunnel.
- With PuTTY: *Connection → SSH → Tunnels*, Source `13001`, Destination `127.0.0.1:<panel port>`.

The username and password are the ones you set in the AdGuard setup wizard.

### Forgot the panel password

The password is stored only as a bcrypt hash in `AdGuardHome.yaml` on the VPS. It cannot be read, only replaced.

1. Stop AdGuard (`systemctl stop AdGuardHome`, or `docker stop <container>`).
2. Make a bcrypt hash: `htpasswd -nbB admin 'new-password'` and take the part after `admin:`.
3. In `AdGuardHome.yaml`, under `users:`, replace the `password:` value with the new hash.
4. Start AdGuard again and log in with the new password.

Back up the file first and keep the old copy private.

## Who may use the resolver

The **DNS → Own DNS server** card shows how the resolver is exposed:

| Mode | Meaning |
|---|---|
| **local** | Listens on loopback only (for example `127.0.0.1:5300`), reachable through DoH or a proxy. |
| **tailnet** | Reachable only by devices in your Tailscale network. |
| **lan** | Reachable from a private network. |
| **public** | Reachable from the internet on a plain DNS port. The app warns: an open resolver can be abused for DNS amplification attacks. Prefer DoH with a secret path, or restrict by firewall. |

## Point devices at it

The card offers two ways, switchable above the steps:

- **DoH address**: an `https://dns.example.net/…` URL (often with a secret path). Paste it into the field on the page; it is only used to fill in the steps in your browser, never saved or sent to the app.
- **Plain DNS by IP**: the server's address (available for tailnet, LAN and public modes).

Per-platform summary (full steps are in the app, tabs *Browser, macOS, Windows, Linux, Android, iPhone, OpenWrt, whole Tailscale network*):

- **Browsers**: Chrome/Edge: *Settings → Privacy and security → Security → Use secure DNS → custom provider*. Firefox: *Settings → Privacy & Security → DNS over HTTPS → custom*. Safari has no custom DoH; use a profile.
- **macOS / iPhone**: install a configuration profile generated from your DoH address, then **delete the downloaded file** (it contains your secret URL).
- **Windows 11**: *Network → DNS server assignment → Manual → IPv4*, then *DNS over HTTPS → On (manual template)*. Windows 10 has no system DoH with a custom address; use the browser.
- **Linux**: `systemd-resolved` speaks DNS-over-TLS but not DoH; run a local `dnsproxy` for system-wide DoH, or set plain DNS with `nmcli`.
- **Android**: *Private DNS* accepts only DNS-over-TLS (a host name, port 853), **not** a DoH URL. Pasting a DoH URL there breaks connectivity. Use an app with a custom DoH server, or Chrome's own setting.
- **OpenWrt**: point `dnsmasq` at the server, or hand it out via DHCP option 6 for selected hosts.
- **Whole Tailscale network**: set the server's Tailscale IP as a global nameserver in the Headscale or Tailscale DNS settings.

## Verify it works

1. In the AdGuard panel open **Query Log** and find the domain you tried. You see the answer and the rule that matched. After any setup change, confirm the device's queries appear there.
2. On a client: `nslookup example.com <server-ip>` (plain DNS), or the browser's DoH test page.
3. If Tailscale's own "Use Tailscale DNS" is on, it can intercept queries; check the Query Log to see who answered.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Panel does not open | The tunnel window must stay open; the local port must be free; the panel port must match (`ss -ltnp \| grep -i adguard` on the VPS). |
| `bind: Address already in use` | Pick another local port, for example `13002`. |
| `Connection refused` in the browser | AdGuard does not listen on that VPS port, or only on another address. |
| Functional check: DNS UDP/TCP fail | AdGuard is not listening on the configured DNS port, or the service is down. |
| Local DoH ok, public DoH fails | The reverse proxy, TLS certificate, or the secret path in `/root/dns-doh-url` is wrong or unreadable by the SSH user. |
| Internet stops after changing Android *Private DNS* | A DoH URL was entered; clear it and set it to *Automatic*. |
| A site does not open | Query Log: find the domain and see whether a filter rule blocked it. |

## Privacy and safety

- Do not share the panel address, tunnel command with your real IP, the DoH URL or `/root/dns-doh-url`.
- Keep the panel off the public internet.
- When posting screenshots, replace hostnames and addresses, as in this guide.

See also: [docs/DNS_CHATMAIL_ru.md](docs/DNS_CHATMAIL_ru.md) (Russian, protocol details), [docs/DNS_CARD_ru.md](docs/DNS_CARD_ru.md), [CHANGELOG.md](CHANGELOG.md).
