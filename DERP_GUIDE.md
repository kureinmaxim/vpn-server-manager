# DERP guide

How to read the DERP information in **Server load**, what a self-hosted DERP relay is, and how to check one. All names, addresses and ports below are examples (`example.net`, documentation IP ranges `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`).

## What DERP is

Tailscale and Headscale devices try to connect **directly** (UDP, NAT traversal). When that fails, traffic goes through a **DERP relay**: a public server both sides can reach. DERP is also used to set up the direct path, so even connections that end up direct start through it.

- A **region** is a named group of DERP servers (for example `fra`, `nyc`). Tailscale publishes public regions; Headscale can add your own.
- Every device picks one **home DERP**: the region with the lowest latency from that device. Other devices contact it through its home DERP when there is no direct path.
- Regions with an ID of 900 or higher are custom ones by convention. An embedded Headscale DERP typically uses 999.

## Reading the Server load window

### Summary above the table

| Line | Meaning |
|---|---|
| **Home DERP of this PC** | The region this PC picked. Chosen by `tailscaled` itself, not by the app. |
| **UDP: Yes / No** | Whether the UDP (STUN) probes to DERP servers got through during the measurement. |
| **Nearest by netcheck** | The region with the lowest latency in the last `tailscale netcheck`. |
| Region badges | The five fastest regions plus all custom ones. The number is a round trip in milliseconds: **this PC ↔ DERP server**. |

With an **exit node selected** on the PC, `netcheck` runs through it, so every latency becomes **PC → exit node → region** and is distorted. The app warns about this. The home DERP is still chosen directly by Tailscale, so it can differ from "nearest by netcheck".

Right after you switch exit nodes, `netcheck` can return no latencies. The app keeps such an empty result for 15 seconds instead of 3 minutes; press **Refresh** after a few seconds.

### Per-server column "Workstation mesh"

| Line | Meaning |
|---|---|
| **In this PC's mesh** | The server is a visible peer in the Tailscale network of the PC running the app. |
| **Exit node (selected / available)** | The peer is the exit node chosen on this PC, or offers to be one. |
| **Coordinator** | The server address matches the control-plane address (Headscale). Behind a reverse proxy this may be the entry node, not Headscale itself. |
| **Path unconfirmed: the peer may be idle** | `tailscale status` shows no direct address for this peer. An idle peer often has none; it does not mean "broken". |
| **Peer home DERP: fra** | The relay **that peer** picked as its nearest. Others reach the peer through it when no direct path exists. It is **not** the route of your traffic and **not** proof that relaying is happening now. A region from your own DERP map is marked *(custom)*. |
| **Check path** | Sends up to three `tailscale ping` packets. Only a *pong* proves the path: *direct `address:port`* or *via DERP region*. The first pong may go through DERP while a direct path is still being built. It is a snapshot with a time, not a guarantee. |

Two peers can show different home DERPs, and that is normal. Each picks the region closest to itself.

## Your own DERP

Run your own relay when public regions are far away, blocked, or you want control. Headscale has a built-in DERP server, so no separate software is required.

Typical requirements:

- **TCP 443** (HTTPS, DERP traffic and `/derp/probe`). If a web server already owns 443, the DERP needs another port or an SNI-based split.
- **UDP 3478** (STUN).
- A public IPv4 on the interface.
- A DNS name and a valid TLS certificate, unless clients are configured otherwise.
- The server's own region in the DERP map with an ID of 900+ (for example `999`), plus `verify_clients` to keep strangers out.

### The "DERP and port availability" block

Expand it under a server row for a read-only check over SSH (no sudo, nothing installed or changed):

| Field | Meaning |
|---|---|
| **Headscale** and version | Whether a Headscale instance was found. |
| **Embedded DERP enabled** / `verify_clients` | Read from the Headscale config. Only an allowlist of DERP fields is read; key paths and the rest of the config never reach the app. |
| `/derp/probe` code | A local HTTPS request to the built-in DERP, with certificate checking. `200` is healthy. |
| **STUN** port listening | Whether the UDP STUN port is bound. |
| **Public regions in config** | Whether the Tailscale public regions are still merged into the map. |
| **Public IPv4 on interface** | A public address is bound locally. Behind NAT this is "No". |
| **TCP 443 / UDP 3478** | Free or busy, with the process name when busy. Useful before deploying a new DERP. |

Badge roles:

- **primary**: local checks pass and at least one visible node uses this region as its home.
- **standby**: local checks pass but no visible node picked it.
- **not responding**: the probe or STUN check failed.

### Limits

- These are **local** checks on the server. They do **not** prove the relay is reachable from the internet. Firewall, NAT and provider restrictions must be tested separately, for example from another network with `tailscale netcheck`.
- The app never edits the Headscale config, services or firewall.
- For Docker, the standard mounts `/etc/headscale` and `config.yaml` are supported. A complex or ambiguous YAML gives "unknown" rather than a guess.

## Quick troubleshooting

| Symptom | What to check |
|---|---|
| All latencies look huge | An exit node is selected: `netcheck` goes through it. Switch it off and press **Refresh**. |
| No latencies at all | You switched exit nodes a moment ago. Wait a few seconds and refresh. |
| `UDP: No` | UDP 3478 is blocked on this network, or the exit node does not pass UDP. |
| Peer shows only a DERP home, no address | The peer is idle. Press **Check path**. |
| Own DERP shows "not responding" | On the server: `/derp/probe` code, whether UDP 3478 is bound, certificate validity, and that nothing else owns TCP 443. |
| Own DERP never becomes "primary" | No visible node picked it. Check the DERP map reaches clients and the latency to it is not worse than public regions. |

Useful commands on a device:

```bash
tailscale netcheck            # latency per region, UDP/IPv4/IPv6 reachability
tailscale status              # peers, direct address, relay
tailscale ping 100.64.0.10    # use a peer's Tailscale address; shows direct or DERP(region)
tailscale debug derp-map      # the DERP map this device received
```

## Privacy

The app shows peer names and addresses only in its own window. It reads no key material from Headscale. When sharing screenshots, replace hostnames, public IPs and tailnet names, as in the examples here.

See also: [docs/README_MONITORING_ru.md](docs/README_MONITORING_ru.md#derp-в-обзоре-загрузки-4111) (Russian, technical details), [CHANGELOG.md](CHANGELOG.md).
