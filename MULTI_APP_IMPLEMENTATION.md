# Running several instances at once

Language: **English** · [Русский](MULTI_APP_IMPLEMENTATION_ru.md)

## Goal

VPN Server Manager can run **more than one copy at the same time** without fighting over ports or sessions. You can open two managers side by side, or run it next to another local Flask app.

Current launchers: `python run.py` (web) and `python run_desktop.py` (desktop). Older notes said `app.py` — that is no longer the entry point.

---

## Architecture

### 1. Dynamic ports

**Problem:** A hard-coded port (for example 5050) may already be in use.

**Solution:** Bind to port `0` so the OS picks a free TCP port.

```python
# Port 0 — the OS assigns a free TCP port
_WSGI_SERVER = make_server('127.0.0.1', 0, app)
SERVER_PORT = _WSGI_SERVER.server_port
print(f"Flask listening on http://127.0.0.1:{SERVER_PORT}")
```

**Benefits:**
- Never clashes with other apps
- Free port is chosen automatically
- Works on Windows, macOS, and Linux

### 2. Unique session cookies

**Problem:** Browsers share cookies per host, so two apps on `127.0.0.1` can mix sessions.

**Solution:** Each app uses its own cookie name.

```python
app.config['SESSION_COOKIE_NAME'] = 'vps_manager_session_vpn'
```

**Benefits:**
- Isolated sessions per instance
- No cookie clash between copies
- Session data stays in the right app

### 3. Isolated data directories

**Problem:** Several instances can overwrite each other’s files.

**Solution:** Each install uses its own data directory.

```python
def get_app_data_dir():
    app_name = "VPNServerManager"
    if is_frozen:  # packaged app
        if sys.platform == 'darwin':  # macOS
            return os.path.join(
                os.path.expanduser("~"),
                "Library", "Application Support",
                app_name,
            )
    else:  # development
        return os.getcwd()
```

Packaged Windows uses `%APPDATA%\VPNServerManager\`; Linux uses `~/.local/share/VPNServerManager/`. Sync between copies is import/export, not a shared file.

**Benefits:**
- Each copy keeps its own data
- Parallel runs do not wipe each other
- Optional sync via export/import

---

## How it starts

### 1. Startup structure

```python
SERVER_PORT = None
_WSGI_SERVER = None

def _start_flask_server():
    """Start Flask on a background thread."""
    global SERVER_PORT, _WSGI_SERVER
    try:
        _WSGI_SERVER = make_server('127.0.0.1', 0, app)
        SERVER_PORT = _WSGI_SERVER.server_port
        print(f"Flask listening on http://127.0.0.1:{SERVER_PORT}")
        _WSGI_SERVER.serve_forever()
    except Exception as e:
        print(f"Flask failed to start: {e}")
```

### 2. Threading

Flask runs on a daemon thread so the desktop window can open immediately:

```python
flask_thread = threading.Thread(target=_start_flask_server)
flask_thread.daemon = True
flask_thread.start()

import time
for _ in range(100):
    if SERVER_PORT:
        break
    time.sleep(0.05)
```

**Benefits:**
- Non-blocking start
- Fast GUI init
- Reliable bind on localhost

### 3. Clean shutdown

```python
@app.route('/shutdown')
def shutdown():
    """Ask the process to stop."""
    os.kill(os.getpid(), signal.SIGINT)
    return 'Server stopping...'

def on_closing():
    """Window close handler."""
    try:
        requests.get(f'http://127.0.0.1:{SERVER_PORT}/shutdown', timeout=1)
    except requests.exceptions.RequestException:
        pass
```

**Benefits:**
- Port is released
- Worker threads stop
- Prefer closing the window, not killing the process

---

## Network

### 1. Localhost only

```python
# Always 127.0.0.1 (not 0.0.0.0)
_WSGI_SERVER = make_server('127.0.0.1', 0, app)
```

**Why:**
- **Security:** only this machine can connect
- **Speed:** loopback is faster than an external interface
- **Isolation:** nothing from the LAN reaches the UI

### 2. Dynamic window URL

```python
window = webview.create_window(
    'VPS Manager',
    f'http://127.0.0.1:{SERVER_PORT or 5050}',
    width=1280,
    height=800,
    resizable=True,
)
```

**Benefits:**
- Window follows the assigned port
- Fallback to 5050 if the port is not ready yet
- Same pattern in web and desktop launchers

---

## Static vs dynamic ports

| | Static port | Dynamic port |
|---|---|---|
| Collisions | High risk | None |
| Setup | Manual | Automatic |
| Debugging | Predictable | Port changes each run |
| Scale | Limited | As many copies as you need |
| Reliability | May fail to bind | Always gets a free port |

---

## Two copies at once

From `/path/to/vpn-server-manager` (never a personal home path):

### First instance

```bash
cd /path/to/vpn-server-manager && python3 run.py
# e.g. http://127.0.0.1:52341
```

Desktop:

```bash
cd /path/to/vpn-server-manager && python3 run_desktop.py
```

### Second instance

```bash
# Another clone or another project, second terminal
cd /path/to/other-copy && python3 run.py
# e.g. http://127.0.0.1:52342
```

### What stays isolated

- **Port 52341:** first app, data A
- **Port 52342:** second app, data B
- **Cookie:** `vps_manager_session_vpn` (per-app name)
- **Data:** separate directories, no overwrite

---

## Checks and cleanup

### Occupied ports

```bash
# macOS / Linux
lsof -i :52341
lsof -i :52342
netstat -an | grep 52341

# Windows
netstat -ano | findstr :52341
```

### Processes

```bash
# macOS / Linux
ps aux | grep "python.*run"
ps -ef | grep "VPNServerManager"
```

### Stuck port

```bash
# macOS / Linux
kill -9 $(lsof -t -i:52341)
pkill -f "VPNServerManager"
```

---

## Development extras

### Environment

```bash
export APP_NAME="VPNServerManager_Dev"
export SESSION_COOKIE_NAME="vps_manager_dev_session"
```

### IDE launch config

VS Code / Cursor `launch.json` (example — still prefer port `0` for packaged apps):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "VPN Server Manager (web)",
            "type": "python",
            "request": "launch",
            "program": "run.py"
        },
        {
            "name": "VPN Server Manager (desktop)",
            "type": "python",
            "request": "launch",
            "program": "run_desktop.py"
        }
    ]
}
```

Fixed ports in `env` (`SERVER_PORT=5050`) are only for local debugging when you want a predictable URL. Production and packaged builds should keep OS-assigned port `0`.

---

## Troubleshooting

### Address already in use

**Symptoms:** `Address already in use`; the app does not start.

**Fix:**
1. Check the port: `lsof -i :PORT` or `netstat -ano | findstr :PORT`
2. Stop the old PID
3. Start again

This only happens if something still binds a **fixed** port. Dynamic port `0` should not hit this.

### Data mixed between windows

**Symptoms:** one window shows the other copy’s servers; data looks lost.

**Fix:**
1. Check cookie names
2. Confirm each copy uses its own data directory
3. Restart both instances

### Slow start

**Symptoms:** long wait before the UI; startup timeouts.

**Fix:**
1. Wait until `SERVER_PORT` is set (the ~5s poll, 100 × 50ms)
2. Check disk / antivirus load on the venv
3. Avoid starting from a slow network share

---

## Performance notes

### Session and temp files

```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

def cleanup_temp_files():
    temp_dir = os.path.join(app_data_dir, "temp")
    for file in os.listdir(temp_dir):
        if file.endswith('.tmp'):
            os.remove(os.path.join(temp_dir, file))
```

### Optional resource log

```python
import psutil

def log_resource_usage():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    cpu_percent = process.cpu_percent()
    print(f"Resources: {memory_mb:.1f}MB RAM, {cpu_percent:.1f}% CPU")
```

---

## Practices

### Developers

- Use dynamic ports in packaged / production builds
- Test two copies side by side before a release
- Log the assigned port
- Shut down through `/shutdown` so the port is freed

### Users

- Close via the window so shutdown runs
- Do not run dozens of copies
- Full export before experiments
- Watch RAM if several desktop windows are open

### Admins

- Monitor listening ports if needed
- Limit processes in a locked-down environment
- Clean up hung PIDs
- Keep start/stop logs for audit

---

## Ideas not implemented

These snippets are sketches only. Use export/import instead of live sync.

```python
def check_port_conflicts():
    """Scan for port clashes before bind."""
    pass

def register_app_instance():
    """Register this copy in a central instance list."""
    pass

def sync_data_between_instances():
    """Live sync between copies — not implemented."""
    pass
```

---

## Summary

VPN Server Manager is built so several copies can run in parallel:

- Parallel start without port clashes
- Isolated data and sessions
- OS-assigned ports
- Localhost-only bind

**Principles:** dynamic ports instead of a fixed one; unique cookies; Flask on a background thread; clean shutdown to release resources.
