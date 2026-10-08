"""Read-only Tailscale view of the application host. Never expose raw prefs."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from urllib.parse import urlsplit


def public_node(node):
    if not isinstance(node, dict): return None
    return {'id': str(node.get('ID', '')), 'name': str(node.get('HostName', '')),
            'dns': str(node.get('DNSName', '')).rstrip('.'),
            'ips': [ip for ip in node.get('TailscaleIPs', []) if isinstance(ip, str)],
            'exit_available': node.get('ExitNodeOption') is True,
            'exit_selected': node.get('ExitNode') is True,
            'cur_addr': str(node.get('CurAddr') or '')[:256],
            'relay': str(node.get('Relay') or '')[:80],
            'online': node.get('Online') is True}


def tailscale_executable():
    executable = shutil.which('tailscale')
    if not executable and os.name == 'nt':
        candidate = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tailscale/tailscale.exe'
        if candidate.is_file(): executable = str(candidate)
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
