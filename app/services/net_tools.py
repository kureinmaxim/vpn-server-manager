"""Bounded, read-only network diagnostics. No shell or user-provided commands."""
import http.client
import ipaddress
import locale
import re
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import quote, urlsplit

import requests


class ToolError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def host_value(value):
    if not isinstance(value, str):
        raise ToolError('host')
    value = value.strip().rstrip('.')
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    try:
        value = value.encode('idna').decode('ascii')
    except UnicodeError:
        raise ToolError('host')
    if len(value) > 253 or not value or any(
        not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', part)
        for part in value.split('.')
    ):
        raise ToolError('host')
    return value


def port_value(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]{1,5}', str(value)):
        raise ToolError('port')
    port = int(value)
    if not 1 <= port <= 65535:
        raise ToolError('port')
    return port


def public_address(host, port):
    """Validate every resolved address, then pin the connection to one address."""
    entries = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not entries or any(not ipaddress.ip_address(e[4][0]).is_global for e in entries):
        raise ToolError('public')
    return entries[0][4][0]


def provider_json(url, params=None):
    # Fixed provider URLs only; ignore machine proxy credentials and redirects.
    with requests.Session() as client:
        client.trust_env = False
        response = client.get(url, params=params, timeout=(5, 10), allow_redirects=False)
        if response.status_code != 200:
            raise ToolError('provider')
        return response.json()


def run_tool(tool, data):
    if tool == 'my-ip':
        return provider_json('https://ipinfo.io/json')
    host = host_value(data.get('host', '')) if tool != 'fetch' else None
    if tool == 'dns':
        record = data.get('record', 'A')
        if record not in ('A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'PTR', 'CAA'):
            raise ToolError('record')
        if record == 'PTR':
            try:
                host = ipaddress.ip_address(host).reverse_pointer
            except ValueError:
                pass
        return provider_json('https://dns.google/resolve', {'name': host, 'type': record})
    if tool == 'whois':
        try:
            ipaddress.ip_address(host)
            kind = 'ip'
        except ValueError:
            kind = 'domain'
        # rdap.org only redirects to the authoritative HTTPS registry. Follow
        # explicitly with the same public-address checks used by HTTP diagnostics.
        url = 'https://rdap.org/' + kind + '/' + quote(host, safe='')
        for _ in range(4):
            result = fetch_url(url)
            if result['status'] in (301, 302, 303, 307, 308):
                from urllib.parse import urljoin
                url = urljoin(url, result['headers'].get('location', ''))
                if urlsplit(url).scheme != 'https':
                    raise ToolError('provider')
                continue
            if result['status'] != 200:
                raise ToolError('provider')
            import json
            try:
                return json.loads(result['body'])
            except ValueError:
                raise ToolError('provider')
        raise ToolError('provider')
    if tool == 'location':
        ip = public_address(host, 443)
        return provider_json('https://ipinfo.io/' + quote(ip, safe='') + '/json')
    if tool == 'fetch':
        return fetch_url(data.get('url', ''))
    port = port_value(data.get('port', 443)) if tool in ('port', 'tls') else 443
    ip = public_address(host, port)
    if tool == 'ping':
        args = ['ping', '-n' if sys.platform == 'win32' else '-c', '4', ip]
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        try:
            result = subprocess.run(args, capture_output=True, timeout=20, **options)
        except FileNotFoundError:
            raise ToolError('ping_missing')
        encoding = 'oem' if sys.platform == 'win32' else locale.getpreferredencoding(False)
        return {'address': ip, 'exit_code': result.returncode,
                'output': (result.stdout + result.stderr).decode(encoding, errors='replace')[:16384]}
    started = time.monotonic()
    if tool == 'port':
        try:
            with socket.create_connection((ip, port), timeout=5):
                return {'address': ip, 'port': port, 'reachable': True,
                        'elapsed_ms': round((time.monotonic() - started) * 1000, 1)}
        except (TimeoutError, ConnectionRefusedError):
            return {'address': ip, 'port': port, 'reachable': False}
    if tool == 'tls':
        with socket.create_connection((ip, port), timeout=5) as raw:
            with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as conn:
                return {'address': ip, 'protocol': conn.version(), 'cipher': conn.cipher(),
                        'verified': True, 'certificate': conn.getpeercert()}
    raise ToolError('tool')


def fetch_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 for c in url):
        raise ToolError('url')
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or parts.username is not None or parts.password is not None:
            raise ToolError('url')
        host = host_value(parts.hostname or '')
        port = port_value(parts.port or (443 if parts.scheme == 'https' else 80))
    except ValueError:
        raise ToolError('url')
    ip = public_address(host, port)
    connection = http.client.HTTPConnection(host, port, timeout=8)
    try:
        raw = socket.create_connection((ip, port), timeout=5)
        connection.sock = raw
        if parts.scheme == 'https':
            connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        stream = connection.sock
        path = parts.path or '/'
        if parts.query:
            path += '?' + parts.query
        connection.request('GET', path, headers={'User-Agent': 'VPNServerManager-NetTools', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        # Bound both time and size, including responses sent a byte at a time.
        deadline = time.monotonic() + 10
        chunks = bytearray()
        while len(chunks) < 65537:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            # response.fp owns the socket when HTTP/1.0 closes the connection.
            stream.settimeout(max(0.1, remaining))
            chunk = response.read1(min(8192, 65537 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        return {'status': response.status, 'reason': response.reason,
                'headers': {k.lower(): v for k, v in response.getheaders()},
                'body': bytes(chunks[:65536]).decode('utf-8', errors='replace'),
                'truncated': len(chunks) > 65536}
    finally:
        connection.close()
