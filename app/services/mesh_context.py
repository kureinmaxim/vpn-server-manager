"""Read-only Tailscale view of the application host. Never expose raw prefs."""
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from urllib.parse import urlsplit


def endpoint_host(value):
    """IP or hostname from a Tailscale endpoint `host:port` or `[ipv6]:port`."""
    if not isinstance(value, str):
        return ''
    value = value.strip()[:128]
    if not value:
        return ''
    if value.startswith('['):
        return value[1:].split(']', 1)[0]
    if value.count(':') == 1:
        return value.rsplit(':', 1)[0]
    return value


def public_node(node):
    if not isinstance(node, dict): return None
    ips = [ip for ip in node.get('TailscaleIPs', []) if isinstance(ip, str)]
    seen = set(ips)
    endpoints = []
    for item in list(node.get('Addrs') or [])[:16] + [node.get('CurAddr')]:
        host = endpoint_host(item)
        if host and host not in seen:
            seen.add(host)
            endpoints.append(host[:64])
        if len(endpoints) >= 8:
            break
    return {'id': str(node.get('ID', '')), 'name': str(node.get('HostName', '')),
            'dns': str(node.get('DNSName', '')).rstrip('.'),
            'ips': ips, 'endpoints': endpoints,
            'exit_available': node.get('ExitNodeOption') is True,
            'exit_selected': node.get('ExitNode') is True,
            'cur_addr': str(node.get('CurAddr') or '')[:256],
            'relay': str(node.get('Relay') or '')[:80],
            'online': node.get('Online') is True}


def _norm(value):
    return str(value or '').strip().lower().rstrip('.')


def node_matches(ip, name, node):
    """True when a server card is this Tailscale node (IP, endpoint or hostname)."""
    if not isinstance(node, dict):
        return False
    address, label = _norm(ip), _norm(name)
    names = {_norm(node.get('name')), _norm(node.get('dns')).split('.')[0]}
    names.discard('')
    if address and address in {_norm(item) for item in list(node.get('ips') or []) + list(node.get('endpoints') or [])}:
        return True
    if address and address == _norm(node.get('dns')):
        return True
    cur = _norm(node.get('cur_addr'))
    if address and cur and (cur == address or cur.startswith(address + ':') or cur.startswith('[' + address + ']')):
        return True
    tokens = {part for part in re.split(r'[\s_./-]+', label) if len(part) >= 3}
    return bool(label) and (label in names or bool(names & tokens))


def card_marks(ip, name, mesh):
    """Icons for a server card from the local mesh. Empty when Tailscale is not ready."""
    if not isinstance(mesh, dict) or mesh.get('state') != 'ready':
        return {}
    address = _norm(ip)
    coordinator = bool(address) and (
        address == _norm(mesh.get('coordinator'))
        or address in {_norm(item) for item in mesh.get('coordinator_ips') or []})
    matches = [node for node in mesh.get('nodes') or [] if node_matches(ip, name, node)]
    peer = matches[0] if len(matches) == 1 else None
    marks = {}
    if coordinator:
        marks['coordinator'] = True
    if peer:
        marks.update(mesh=True, online=peer.get('online') is True,
                     exit_selected=peer.get('exit_selected') is True,
                     exit_available=peer.get('exit_available') is True,
                     relay=str(peer.get('relay') or ''), name=str(peer.get('name') or ''))
    return marks


def _fallback_paths():
    if os.name == 'nt':
        return [Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tailscale/tailscale.exe']
    if sys.platform == 'darwin':
        # A Finder-launched .app gets PATH=/usr/bin:/bin:/usr/sbin:/sbin, so the CLI is not found.
        return [Path('/usr/local/bin/tailscale'), Path('/opt/homebrew/bin/tailscale'),
                Path('/Applications/Tailscale.app/Contents/MacOS/Tailscale')]
    return []


def tailscale_executable():
    executable = shutil.which('tailscale')
    if not executable:
        executable = next((str(p) for p in _fallback_paths() if p.is_file() and os.access(p, os.X_OK)), None)
    return executable


def read_tailscale(executable, args, timeout=4):
    result = subprocess.run([executable, *args], capture_output=True, timeout=timeout,
                            encoding='utf-8', errors='replace',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError('unavailable')
    # Windows netcheck can prefix its JSON with diagnostic messages.
    data, _ = json.JSONDecoder().raw_decode(result.stdout[result.stdout.index('{'):])
    if not isinstance(data, dict): raise ValueError('unavailable')
    return data


def local_mesh():
    executable = tailscale_executable()
    if not executable: return {'state': 'unavailable', 'nodes': []}
    def read(args):
        return read_tailscale(executable, args)
    try:
        status = read(['status', '--json'])
        if status.get('BackendState') != 'Running': return {'state': 'disconnected', 'nodes': []}
        peers = status.get('Peer') or {}
        nodes = [public_node(value) for value in [status.get('Self'), *peers.values()]]
        result = {'state': 'ready', 'nodes': [node for node in nodes if node],
                  'name': (status.get('CurrentTailnet') or {}).get('Name', ''),
                  'host': (status.get('Self') or {}).get('HostName', ''),
                  'home_relay': str((status.get('Self') or {}).get('Relay') or ''),
                  'coordinator': '', 'coordinator_ips': []}
        try:
            # Prefs may contain private authentication material. Return only hostname.
            prefs = read(['debug', 'prefs'])
            hostname = urlsplit(prefs.get('ControlURL', '')).hostname or ''
            result['coordinator'] = hostname
            if hostname:
                pool = ThreadPoolExecutor(max_workers=1)
                try:
                    addresses = pool.submit(socket.getaddrinfo, hostname, None).result(timeout=2)
                    result['coordinator_ips'] = sorted({item[4][0] for item in addresses})
                except (OSError, TimeoutError): pass
                finally: pool.shutdown(wait=False)
        except (OSError, ValueError, TypeError, subprocess.SubprocessError): pass
        return result
    except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
        return {'state': 'unavailable', 'nodes': []}


def remote_mesh(output):
    try:
        raw = output.split('VPN_MESH_BEGIN\n', 1)[1].split('\nVPN_MESH_END', 1)[0]
        data = json.loads(raw)
        if data.get('BackendState') != 'Running': return {'state': 'disconnected'}
        return {'state': 'ready', 'self': public_node(data.get('Self'))}
    except (IndexError, ValueError, AttributeError, TypeError):
        return {'state': 'unavailable'}
