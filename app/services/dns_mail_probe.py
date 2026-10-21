"""Read-only DNS/mail probes. Standard library only: also executed over trusted SSH.

Never return exception messages, URLs, HTTP headers/bodies or SMTP banners. This
module must remain independent of Flask and application credentials.
"""
import concurrent.futures
import datetime
import http.client
import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import stat
import struct
import subprocess
import time
from urllib.parse import urlsplit

ROLE_NAMES = {'adguard': 'AdGuard Home / DNS', 'chatmail': 'Chatmail relay'}
CORE = ('postfix@-', 'postfix', 'dovecot', 'doveauth', 'chatmail-metadata',
        'filtermail', 'filtermail-incoming', 'filtermail-transport')
EXTRA = ('nginx', 'unbound', 'turnserver', 'iroh-relay', 'lastlogin',
         'opendkim', 'acmetool-redirector')
UNITS = ('AdGuardHome', 'adguardhome', 'adguard-home') + CORE + EXTRA


class ProbeError(Exception):
    """Fixed public reason, never remote exception text."""


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def command(args):
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=4, check=False)
        return result.returncode, result.stdout[:65536].decode('utf-8', 'replace')
    except FileNotFoundError:
        return 127, ''
    except (OSError, subprocess.TimeoutExpired):
        return 126, ''


def discover(run=command):
    """Read allowlisted systemd properties and Docker metadata, never env/argv."""
    code, output = run(['systemctl', 'show', '--no-pager', '-p', 'Id', '-p', 'LoadState',
                        '-p', 'ActiveState', '--'] + [u + '.service' for u in UNITS])
    units, observed = {}, set()
    for block in output.strip().split('\n\n'):
        values = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        name = values.get('Id', '').removesuffix('.service')
        if name in UNITS and values.get('LoadState'):
            observed.add(name)
        if name in UNITS and values.get('LoadState') not in (None, 'not-found'):
            units[name] = values.get('ActiveState', 'unknown')
    # systemctl can exit nonzero when some named units are absent. Evidence for
    # each unit remains useful; an empty/failed probe is never proof of absence.
    unit_access = code == 0 or set(UNITS).issubset(observed)
    fmt = '{{.Names}}\t{{.Image}}\t{{.State}}\t{{.Ports}}\t{{.Label "com.docker.compose.service"}}'
    docker_code, output = run(['docker', 'ps', '-a', '--format', fmt])
    containers = []
    if docker_code == 0:
        for line in output.splitlines()[:256]:
            parts = line.split('\t')
            if len(parts) != 5:
                continue
            name, image, state, ports, service = parts
            # The image is authoritative; Compose label alone isn't sufficient.
            if re.search(r'(^|/)adguard(?:/adguardhome|home)(?=[:@]|$)', image, re.I):
                containers.append({'name': name[:128], 'kind': 'container',
                    'status': 'active' if state == 'running' else 'inactive',
                    'version': image.split(':')[-1][:64] if ':' in image else None,
                    'ports': ports[:1024], 'compose_service': service[:64], 'optional': False})
    dns = containers + [component(n, units[n]) for n in UNITS[:3] if n in units]
    markers = [n for n in CORE[3:] if n in units]
    mail_found = len(markers) >= 2 and ('postfix@-' in units or 'postfix' in units) and 'dovecot' in units
    results = []
    for role, found, accessible in [('adguard', bool(dns), unit_access and docker_code in (0, 127)),
                                     ('chatmail', mail_found, unit_access)]:
        rows = dns if role == 'adguard' else [component(n, units.get(n, 'not_installed' if n in observed or unit_access else 'unknown'), n in EXTRA)
            for n in CORE + EXTRA if n != 'postfix' or 'postfix@-' not in units]
        if role == 'chatmail' and 'postfix@-' not in units and 'postfix' in units:
            rows = [r for r in rows if r['name'] != 'postfix@-.service']
        core = [r for r in rows if not r['optional']]
        active = sum(r['status'] == 'active' for r in core)
        runtime = ('running' if active == len(core) else 'partial' if active else 'stopped') if found else 'unknown'
        results.append({'key': role, 'name': ROLE_NAMES[role], 'detected': found,
                        'state': runtime, 'components': rows if found else [],
                        'discovery': 'detected' if found else 'not_found' if accessible else 'unavailable',
                        'coverage': 'complete' if accessible else 'partial',
                        'functional': 'unconfigured', 'checked_at': timestamp(), 'source': 'ssh'})
    return results


def component(name, state, optional=False):
    return {'name': name + '.service', 'kind': 'unit', 'status': state, 'optional': optional}


def domain(value):
    if not isinstance(value, str) or len(value) > 253:
        raise ProbeError('configuration')
    value = value.rstrip('.').encode('idna').decode('ascii').lower()
    if not value or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', p) for p in value.split('.')):
        raise ProbeError('configuration')
    return value


def query(name):
    labels = domain(name).split('.')
    return struct.pack('!6H', secrets.randbelow(65536), 0x100, 1, 0, 0, 0) + b''.join(
        bytes([len(p)]) + p.encode('ascii') for p in labels) + b'\0\0\1\0\1'


def dns_name(data, offset):
    labels, seen, end = [], set(), None
    for _ in range(128):
        if offset >= len(data) or offset in seen:
            raise ProbeError('dns_format')
        seen.add(offset)
        size = data[offset]
        if size & 0xc0 == 0xc0:
            if offset + 1 >= len(data):
                raise ProbeError('dns_format')
            if end is None:
                end = offset + 2
            offset = ((size & 63) << 8) | data[offset + 1]
            continue
        offset += 1
        if size == 0:
            return b'.'.join(labels).lower(), end or offset
        if size > 63 or offset + size > len(data):
            raise ProbeError('dns_format')
        labels.append(data[offset:offset + size])
        offset += size
    raise ProbeError('dns_format')


def parse_dns(data, request, expected='NOERROR'):
    if len(data) < 12:
        raise ProbeError('dns_format')
    ident, flags, qd, an, ns, ar = struct.unpack('!6H', data[:12])
    if data[:2] != request[:2] or not flags & 0x8000 or flags & 0x7800 or qd != 1:
        raise ProbeError('dns_format')
    if flags & 0x200:
        raise ProbeError('dns_truncated')
    name, offset = dns_name(data, 12)
    wanted, qend = dns_name(request, 12)
    if name != wanted or data[offset:offset + 4] != request[qend:qend + 4]:
        raise ProbeError('dns_format')
    offset += 4
    addresses, aliases = {}, {}
    extended_rcode = 0
    for i in range(an + ns + ar):
        owner, offset = dns_name(data, offset)
        if offset + 10 > len(data):
            raise ProbeError('dns_format')
        kind, klass, ttl, length = struct.unpack('!HHIH', data[offset:offset + 10])
        offset += 10
        value = data[offset:offset + length]
        if len(value) != length:
            raise ProbeError('dns_format')
        if kind == 41:
            extended_rcode = ttl >> 24
        if i < an and klass == 1:
            if kind == 1:
                if length != 4:
                    raise ProbeError('dns_format')
                addresses.setdefault(owner, []).append(str(ipaddress.ip_address(value)))
            elif kind == 5:
                target, end = dns_name(data, offset)
                if end != offset + length:
                    raise ProbeError('dns_format')
                aliases[owner] = target
        offset += length
    if offset != len(data):
        raise ProbeError('dns_format')
    code = (extended_rcode << 4) | (flags & 15)
    rcode = {0: 'NOERROR', 2: 'SERVFAIL', 3: 'NXDOMAIN', 5: 'REFUSED'}.get(code, str(code))
    target, visited = wanted, set()
    while target in aliases:
        if target in visited or len(visited) >= 32:
            raise ProbeError('dns_format')
        visited.add(target)
        target = aliases[target]
    answers = addresses.get(target, [])
    ok = rcode == expected and (an == 0 if expected == 'NXDOMAIN' else bool(answers))
    return {'state': 'healthy' if ok else 'error', 'reason': 'dns_ok' if ok else 'dns_rcode',
            'rcode': rcode, 'expected': expected, 'answers': answers[:16], 'answer_count': an}


def receive(sock, size, deadline=None):
    data = b''
    while len(data) < size:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            sock.settimeout(min(4, remaining))
        part = sock.recv(size - len(data))
        if not part:
            raise ProbeError('protocol')
        data += part
    return data


def dns_check(address, port, name, expected='NOERROR', tcp=False):
    packet = query(name)
    deadline = time.monotonic() + 6
    family = socket.AF_INET6 if ':' in address else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM) as conn:
        conn.settimeout(4)
        conn.connect((address, port))
        conn.sendall(struct.pack('!H', len(packet)) + packet if tcp else packet)
        response = receive(conn, struct.unpack('!H', receive(conn, 2, deadline))[0], deadline) if tcp else conn.recv(65535)
    return parse_dns(response, packet, expected)


def public_ip(host, port):
    entries = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not entries or any(not ipaddress.ip_address(e[4][0]).is_global for e in entries):
        raise ProbeError('public_address')
    return entries[0][4][0]


def certificate(conn):
    cert = conn.getpeercert()
    expires = cert.get('notAfter')
    return {'tls': conn.version(), 'certificate_verified': True,
            'certificate_expires': expires,
            'certificate_days': int((ssl.cert_time_to_seconds(expires) - time.time()) // 86400) if expires else None}


def doh_check(url, name, expected='NOERROR', local=False):
    """Strict HTTPS, pinned public address, no proxies/redirects or response echo."""
    parsed = urlsplit(url)
    if (len(url) > 2048 or any(ord(c) < 33 for c in url) or parsed.username or parsed.password
            or parsed.fragment or not parsed.hostname):
        raise ProbeError('configuration')
    host, port = parsed.hostname, parsed.port or (80 if local else 443)
    if local:
        if parsed.scheme != 'http' or host not in ('127.0.0.1', '::1'):
            raise ProbeError('configuration')
        address = host
    else:
        if parsed.scheme != 'https':
            raise ProbeError('configuration')
        address = public_ip(host, port)
    packet = query(name)
    conn = http.client.HTTPConnection(host, port, timeout=4)
    raw = socket.create_connection((address, port), timeout=4)
    try:
        conn.sock = raw if local else ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        cert = {} if local else certificate(conn.sock)
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        conn.request('POST', path, body=packet, headers={'Accept': 'application/dns-message',
                                                      'Content-Type': 'application/dns-message'})
        response = conn.getresponse()
        if response.status != 200:
            raise ProbeError('http_status')
        if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/dns-message':
            raise ProbeError('doh_content_type')
        data, deadline = bytearray(), time.monotonic() + 6
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError()
            part = response.read1(min(4096, 65536 - len(data)))
            data.extend(part)
            if len(data) >= 65536:
                raise ProbeError('dns_format')
            if not part:
                break
        return dict(parse_dns(bytes(data), packet, expected), **cert)
    finally:
        conn.close()
        raw.close()


def read_doh_url(path):
    # Bounded regular file, no symlink traversal. Secret remains inside remote process.
    if not path.startswith('/') or '..' in path.split('/'):
        raise ProbeError('configuration')
    parent = path
    while parent != '/':
        if stat.S_ISLNK(os.lstat(parent).st_mode):
            raise ProbeError('configuration')
        parent = os.path.dirname(parent)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 2048:
            raise ProbeError('configuration')
        return handle.read(2049).decode('utf-8').strip()


def line(sock, deadline):
    value = bytearray()
    for _ in range(2048):
        value.extend(receive(sock, 1, deadline))
        if value.endswith(b'\r\n'):
            return bytes(value)
    raise ProbeError('protocol')


def smtp_reply(sock, expected, deadline):
    for _ in range(32):
        value = line(sock, deadline)
        if not value.startswith(expected):
            raise ProbeError('protocol')
        if value[3:4] == b' ':
            return
        if value[3:4] != b'-':
            break
    raise ProbeError('protocol')


def mail_check(host, address, port, protocol, implicit):
    """Greeting and TLS only. No AUTH, MAIL, RCPT, DATA or account creation."""
    deadline = time.monotonic() + 10
    conn = socket.create_connection((address, port), timeout=4)
    try:
        context = ssl.create_default_context()
        if implicit:
            conn = context.wrap_socket(conn, server_hostname=host)
        if protocol == 'smtp':
            smtp_reply(conn, b'220', deadline)
            conn.sendall(b'EHLO diagnostic.invalid\r\n')
            smtp_reply(conn, b'250', deadline)
            if not implicit:
                conn.sendall(b'STARTTLS\r\n')
                smtp_reply(conn, b'220', deadline)
                conn = context.wrap_socket(conn, server_hostname=host)
                conn.sendall(b'EHLO diagnostic.invalid\r\n')
                smtp_reply(conn, b'250', deadline)
        else:
            if not line(conn, deadline).upper().startswith(b'* OK '):
                raise ProbeError('protocol')
            if not implicit:
                conn.sendall(b'a1 STARTTLS\r\n')
                for _ in range(32):
                    value = line(conn, deadline).upper()
                    if value.startswith(b'A1 OK '):
                        break
                    if not value.startswith(b'* '):
                        raise ProbeError('protocol')
                else:
                    raise ProbeError('protocol')
                conn = context.wrap_socket(conn, server_hostname=host)
        return dict(state='healthy', reason='mail_tls_ok', **certificate(conn))
    finally:
        conn.close()


def turn_check(port):
    # STUN binding proves only STUN reachability, NOT TURN allocation/relaying.
    transaction = secrets.token_bytes(12)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
        conn.settimeout(4)
        conn.connect(('127.0.0.1', port))
        conn.send(struct.pack('!HHI', 1, 0, 0x2112a442) + transaction)
        answer = conn.recv(4096)
    if len(answer) < 20 or answer[:2] != b'\x01\x01' or answer[4:20] != struct.pack('!I', 0x2112a442) + transaction:
        raise ProbeError('protocol')
    if struct.unpack('!H', answer[2:4])[0] != len(answer) - 20:
        raise ProbeError('protocol')
    return {'state': 'partial', 'reason': 'stun_only'}


def iroh_check(port):
    with socket.create_connection(('127.0.0.1', port), timeout=4):
        return {'state': 'partial', 'reason': 'tcp_only'}


def checked(name, fn, source='ssh'):
    started = time.monotonic()
    try:
        result = fn()
    except ssl.SSLCertVerificationError:
        result = {'state': 'error', 'reason': 'certificate'}
    except PermissionError:
        result = {'state': 'unavailable', 'reason': 'permissions'}
    except FileNotFoundError:
        result = {'state': 'unconfigured', 'reason': 'missing_file'}
    except (TimeoutError, socket.timeout):
        result = {'state': 'unavailable', 'reason': 'timeout'}
    except ProbeError as exc:
        result = {'state': 'error', 'reason': str(exc)}
    except Exception:
        # Including HTTP errors whose string/repr may contain the secret URL.
        result = {'state': 'unavailable', 'reason': 'connection'}
    return dict(result, name=name, source=source, checked_at=timestamp(),
                elapsed_ms=round((time.monotonic() - started) * 1000, 1))


def diagnose(config):
    role, name, expected = config['role'], config['query'], config['expected']
    if role == 'adguard':
        jobs = [ ('DNS UDP', lambda: dns_check('127.0.0.1', config['dns_port'], name, expected)),
                 ('DNS TCP', lambda: dns_check('127.0.0.1', config['dns_port'], name, expected, True)),
                 ('Local DoH', lambda: doh_check('http://127.0.0.1:%d/dns-query' % config['doh_port'], name, expected, True)),
                 ('Public DoH', lambda: doh_check(read_doh_url(config['doh_file']), name, expected)) ]
    else:
        host = config['mail_domain']
        jobs = []
        for key, protocol, implicit in [('smtp', 'smtp', False), ('submission', 'smtp', False),
                ('smtps', 'smtp', True), ('imap', 'imap', False), ('imaps', 'imap', True)]:
            port = config[key + '_port']
            if port:
                def check(p=port, proto=protocol, tls=implicit):
                    if not host:
                        return {'state': 'unconfigured', 'reason': 'mail_domain'}
                    return mail_check(host, '127.0.0.1', p, proto, tls)
                jobs.append((key.upper(), check))
        if config['turn_port']:
            jobs.append(('TURN / STUN', lambda: turn_check(config['turn_port'])))
        if config['iroh_port']:
            jobs.append(('iroh TCP', lambda: iroh_check(config['iroh_port'])))
    if not jobs:
        return [checked('Chatmail', lambda: {'state': 'unconfigured', 'reason': 'configuration'})]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda job: checked(*job), jobs))


if __name__ == '__main__':
    import signal
    import sys
    signal.alarm(30)
    try:
        options = json.loads(sys.stdin.read(8192))
        result = discover() if options.get('mode') == 'discover' else diagnose(options)
        print(json.dumps(result))
    except Exception:
        print(json.dumps({'error': 'probe_unavailable'}))
