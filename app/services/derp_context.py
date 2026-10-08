"""Bounded, cached read-only DERP diagnostics on the application host."""
import math
import ipaddress
import re
import subprocess
import threading
import time
from urllib.parse import urlsplit

from .mesh_context import read_tailscale, tailscale_executable

_lock = threading.Lock()
_cache = None
_expires = 0


def summarize_derp(status, report, derp_map, coordinator=''):
    regions = []
    latencies = report.get('RegionLatency') or {}
    for key, region in (derp_map.get('Regions') or {}).items():
        try:
            region_id = int(region.get('RegionID', key))
            value = latencies.get(str(region_id))
            latency = float(value) / 1_000_000 if value is not None else None
            if latency is not None and (not math.isfinite(latency) or latency < 0): latency = None
            hosts = [str(node.get('HostName') or '').lower().rstrip('.')
                     for node in region.get('Nodes', []) if isinstance(node, dict)]
            regions.append({'id': region_id, 'code': str(region.get('RegionCode') or key)[:80],
                            'name': str(region.get('RegionName') or '')[:160],
                            'hosts': hosts, 'latency_ms': latency,
                            'own': region_id >= 900 or bool(coordinator and coordinator.lower().rstrip('.') in hosts)})
        except (ValueError, TypeError, AttributeError):
            continue
    regions.sort(key=lambda item: (item['latency_ms'] is None, item['latency_ms'] or 0, item['id']))
    nearest = [r for r in regions if r['latency_ms'] is not None][:5]
    shown = nearest + [r for r in regions if r['own'] and r not in nearest]
    peers = [node for node in (status.get('Peer') or {}).values() if isinstance(node, dict)]
    selected = next((p for p in peers if p.get('ExitNode') is True), None)
    exit_status = status.get('ExitNodeStatus') or {}
    if selected is None and exit_status:
        selected = next((p for p in peers if p.get('ID') == exit_status.get('ID')), {})
    preferred = next((r['code'] for r in regions if r['id'] == report.get('PreferredDERP')), '')
    return {'state': 'ready' if regions else 'unavailable',
            'home_relay': str((status.get('Self') or {}).get('Relay') or '')[:80],
            'udp': report.get('UDP') if isinstance(report.get('UDP'), bool) else None,
            'preferred': preferred, 'regions': shown,
            'exit_selected': selected is not None,
            'exit_name': str((selected or {}).get('HostName') or '')[:160],
            'checked_at': int(time.time()), 'cache_seconds': 180}


def local_derp():
    global _cache, _expires
    # Serialize netcheck and coalesce concurrent viewers into the same cached result.
    if not _lock.acquire(timeout=12): return {'state': 'unavailable'}
    try:
        if _cache is not None and time.monotonic() < _expires: return _cache
        executable = tailscale_executable()
        result = {'state': 'unavailable'}
        deadline = time.monotonic() + 12
        if executable:
            def read(args, cap=3):
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise ValueError('timeout')
                return read_tailscale(executable, args, timeout=min(cap, remaining))
            try:
                status = read(['status', '--json'])
                if status.get('BackendState') != 'Running': raise ValueError('disconnected')
                try:
                    coordinator = urlsplit(read(['debug', 'prefs']).get('ControlURL', '')).hostname or ''
                except (OSError, ValueError, TypeError, subprocess.SubprocessError): coordinator = ''
                derp_map = read(['debug', 'derp-map'])
                try:
                    report = read(['netcheck', '--format=json'], cap=12)
                except (OSError, ValueError, TypeError, subprocess.SubprocessError): report = {}
                result = summarize_derp(status, report, derp_map, coordinator)
            except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError): pass
        _cache = result
        _expires = time.monotonic() + (180 if result['state'] == 'ready' else 15)
        return result
    finally:
        _lock.release()


def parse_ping(output):
    """Only a pong confirms a path. DERP may be followed by a direct pong."""
    result = {'state': 'unknown'}
    for line in output.splitlines():
        match = re.fullmatch(r'pong from .+ \([^)]+\) via (.+) in [0-9.a-zµμ]+', line.strip())
        if not match: continue
        via = match.group(1)
        relay = re.fullmatch(r'DERP\(([\w.-]{1,80})\)', via)
        if relay:
            result = {'state': 'relay', 'relay': relay.group(1)}
            continue
        try:
            host, port = via.rsplit(':', 1)
            ipaddress.ip_address(host.strip('[]'))
            if 0 < int(port) <= 65535: result = {'state': 'direct', 'address': via}
        except ValueError:
            result = {'state': 'unknown'}
    return {**result, 'checked_at': int(time.time())}


def check_peer_path(node_id):
    executable = tailscale_executable()
    if not executable: return {'state': 'unknown'}
    try:
        status = read_tailscale(executable, ['status', '--json'], timeout=3)
        if status.get('BackendState') != 'Running': return {'state': 'unknown'}
        peers = [p for p in (status.get('Peer') or {}).values() if isinstance(p, dict) and p.get('ID') == node_id]
        if len(peers) != 1: return {'state': 'unknown'}
        # The browser supplies an ID only; resolve it to a current visible peer IP.
        address = str(ipaddress.ip_address(peers[0]['TailscaleIPs'][0]))
        try:
            process = subprocess.run([executable, 'ping', '--c=3', '--timeout=2s', '--until-direct=true', address],
                capture_output=True, timeout=10, encoding='utf-8', errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            output = process.stdout
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ''
            if isinstance(output, bytes): output = output.decode('utf-8', errors='replace')
        if len(output) > 65536: return {'state': 'unknown'}
        return parse_ping(output)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, subprocess.SubprocessError):
        return {'state': 'unknown'}
