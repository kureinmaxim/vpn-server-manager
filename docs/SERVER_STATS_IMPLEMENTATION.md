# Server Status Modal: Implementation and SSH Commands

## Overview
This document explains how the server status modal is implemented and which SSH commands are executed on remote hosts to collect system metrics. The feature fetches data via SSH, renders a Bootstrap modal with CPU/memory/disk/process/network/Docker info, and auto-refreshes every 10 seconds.

## Data Flow
- UI button "Статус" on a server card calls `GET /server/<id>/stats`.
- Backend opens an SSH connection using Paramiko (password auth) and executes a set of commands.
- The response is normalized into a single JSON object `stats` consumed by frontend JS.
- The modal renders the metrics and sets a refresh timer that clears on modal close.

## Backend Implementation
- SSH client: Paramiko `SSHClient` with `allow_agent=False` and `look_for_keys=False` to force password-based auth.
- Timeout: default 8–10 seconds per command.
- Helpers:
  - `_ssh_run(ssh, cmd, timeout=8) -> str` — executes a command and returns stdout/stderr.
  - `_collect_stats_via_ssh(host, user, password, port=22) -> dict` — collects and parses metrics and returns a JSON-serializable dict.

### OS and Tool Detection
- OS name: `cat /etc/os-release` (parse `PRETTY_NAME` / `ID` / `ID_LIKE`), fallback: `uname -sr`
- BusyBox/Toybox presence:
  - `command -v busybox >/dev/null 2>&1 || echo missing`
  - `command -v toybox >/dev/null 2>&1 || echo missing`
- Package manager detection (first found is used to build install hints):
  - `command -v apt dnf yum apk pacman zypper opkg | head -n1`

### Missing Tools Check
For full diagnostics the app expects: `top`, `free`, `df`, `ps`, `ip` or `ifconfig`.
- Generic check: `command -v <tool> >/dev/null 2>&1 || echo <tool>`
- BusyBox/Toybox applets check (if classic tools missing): `busybox --list | grep -E '^(top|free|df|ps|ip|ifconfig)$'`
- Result is presented in the modal with an install hint.

### Metrics Collection Commands
Below are the commands (with fallbacks) executed to gather each metric. Implementations prefer `/proc/*` and POSIX tools; on minimal images fallbacks rely on BusyBox toy applets when available.

#### Uptime
- `uptime -p || uptime || cat /proc/uptime`

#### Load Average
- `cat /proc/loadavg || uptime`

#### CPU Usage (%), Cores, Kernel, Model
- Usage (preferred, accurate): read `/proc/stat` twice and compute deltas (user,nice,system,idle,iowait,irq,softirq,steal):
  - `cat /proc/stat | head -n1` (sleep ~0.3s) then `cat /proc/stat | head -n1` again; compute `1 - idleDelta/totalDelta`.
- Fallback (if delta not possible):
  - `top -b -n1 | head -n5` (parse CPU line)
- Cores:
  - `nproc || grep -c '^processor' /proc/cpuinfo`
- Kernel:
  - `uname -r`
- Model (best-effort):
  - `grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-`

#### Memory and Swap
- Prefer `free -m`:
  - `free -m`
- Fallback via `/proc/meminfo`:
  - `cat /proc/meminfo` (parse `MemTotal`, `MemAvailable`, `MemFree`, `SwapTotal`, `SwapFree`)

#### Disks (Space)
- POSIX layout with stable columns:
  - `df -hP | tail -n +2` (fields: `Filesystem Size Used Avail Use% Mounted on`)

#### Inodes
- Inode usage per mount point:
  - `df -iP | tail -n +2` (fields: `Inodes IUsed IFree IUse% Mounted on`)

#### Processes (Top by CPU)
- Full-featured ps:
  - `ps aux --sort -%cpu -o pid,comm,pcpu,pmem | head -n 11`
- BusyBox fallback (no %CPU/%MEM in output):
  - `busybox ps w | head -n 11`

#### Network Interfaces and Addresses
- Preferred (iproute2):
  - `ip -o -4 addr show | awk '{print $2" "$4}'`
- Fallback (net-tools):
  - `ifconfig -a` (parse interface name and inet addr)

#### Network Traffic (RX/TX) per Interface
- Read counters directly from sysfs:
  - `cat /sys/class/net/*/statistics/rx_bytes`
  - `cat /sys/class/net/*/statistics/tx_bytes`

#### Docker Presence and Running Containers
- Presence:
  - `command -v docker >/dev/null 2>&1 && echo present || echo missing`
- Running containers count (if present):
  - `docker ps -q | wc -l`

### Install Hints for Missing Tools
An install command is generated based on detected OS/manager. Examples:
- Debian/Ubuntu (apt):
  - `sudo apt update && sudo apt install -y procps iproute2 net-tools coreutils util-linux findutils`
- RHEL/CentOS/Fedora (dnf/yum):
  - `sudo dnf install -y procps-ng iproute net-tools coreutils util-linux findutils`
- Alpine (apk):
  - `sudo apk add procps iproute2 net-tools coreutils util-linux findutils`
- Arch (pacman):
  - `sudo pacman -Sy --noconfirm procps-ng iproute2 net-tools coreutils util-linux findutils`
- openSUSE (zypper):
  - `sudo zypper install -y procps iproute2 net-tools coreutils util-linux findutils`
- OpenWrt (opkg):
  - `sudo opkg update && sudo opkg install procps-ng ip-full net-tools coreutils util-linux findutils`

## Frontend Implementation
- Route: `GET /server/<id>/stats` returns `{ ok, server_id, stats }` or `{ error, exception }`.
- Modal builds HTML dynamically.
- Auto-refresh: `setInterval(fetchAndRender, 10000)`; cleared in `hidden.bs.modal` to avoid leaks.
- RX/TX are shown as Bootstrap badges next to each interface.
- If `missing_tools` present, a yellow alert with a copyable install command is displayed.

## Error Handling and Robustness
- SSH exceptions (`AuthenticationException`, `SSHException`, timeouts) are handled and returned as `{ error, exception }`.
- If a metric command fails, fallbacks are attempted; fields may be omitted or set to `-`.
- For minimal images (BusyBox/Toybox), simplified output is parsed when classic tools are missing.

## Security Notes
- Password-based SSH only; keys/agent are disabled explicitly.
- Sensitive values are not logged.
- Command outputs are trimmed and sanitized before JSON serialization.

## Response Schema (Stats)
```json
{
  "uptime": "string",
  "load": { "1m": "string", "5m": "string", "15m": "string" },
  "cpu": { "used_pct": 0, "cores": 0, "kernel": "" },
  "mem": { "total_mb": 0, "used_mb": 0, "avail_mb": 0, "used_pct": 0 },
  "swap": { "total_mb": 0, "used_mb": 0, "used_pct": 0 },
  "disks": [ { "mount": "", "size": "", "used": "", "avail": "", "pcent": "" } ],
  "inodes": [ { "mount": "", "inodes": "", "iused": "", "ipcent": "" } ],
  "processes": [ { "pid": "", "cmd": "", "cpu": "", "mem": "" } ],
  "net": [ { "iface": "", "addr": "" } ],
  "traffic": [ { "iface": "", "rx_bytes": 0, "tx_bytes": 0 } ],
  "docker": { "present": false, "running": 0 },
  "missing_tools": [ "top", "free", "df", "ps", "ip", "ifconfig" ],
  "install_hint": "string"
}
```

## Appendix: Command Summary
- OS: `cat /etc/os-release`, `uname -sr`
- BusyBox/Toybox: `command -v busybox`, `command -v toybox`, `busybox --list`
- Pkg manager: `command -v apt dnf yum apk pacman zypper opkg | head -n1`
- Uptime/Load: `uptime -p`, `cat /proc/uptime`, `cat /proc/loadavg`
- CPU: `cat /proc/stat` (delta), `top -b -n1`, `nproc`, `grep -c '^processor' /proc/cpuinfo`, `uname -r`, `grep -m1 'model name' /proc/cpuinfo`
- Memory/Swap: `free -m`, `cat /proc/meminfo`
- Disks: `df -hP`, Inodes: `df -iP`
- Processes: `ps aux --sort -%cpu -o pid,comm,pcpu,pmem`, `busybox ps w`
- Network: `ip -o -4 addr show`, `ifconfig -a`, `cat /sys/class/net/*/statistics/{rx_bytes,tx_bytes}`
- Docker: `command -v docker`, `docker ps -q | wc -l`
