import json
import ssl
import struct
import uuid
from unittest.mock import Mock

import pytest

from app.services import dns_mail_probe as p
from app.services.dns_mail import settings, remote_probe, discovery_rows, remember, annotate


def answer(request, rcode=0, address=b'\xc0\x00\x02\x01'):
    count = 1 if rcode == 0 else 0
    header = request[:2] + struct.pack('!5H', 0x8180 | rcode, 1, count, 0, 0)
    return header + request[12:] + (b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 60, 4) + address if count else b'')


@pytest.mark.parametrize('rcode,expected,state', [(0, 'NOERROR', 'healthy'), (2, 'NOERROR', 'error'),
                                                (3, 'NOERROR', 'error'), (3, 'NXDOMAIN', 'healthy')])
def test_dns_rcode_and_contents(rcode, expected, state):
    packet = p.query('example.com')
    result = p.parse_dns(answer(packet, rcode), packet, expected)
    assert result['state'] == state
    assert result['answer_count'] == (1 if rcode == 0 else 0)


def test_dns_rejects_mismatch_truncation_and_pointer_loop():
    packet = p.query('example.com')
    good = answer(packet)
    for bad in (good[:-1], bytes([good[0] ^ 1]) + good[1:], good[:12] + b'\xc0\x0c' + good[14:],
                good[:2] + b'\x83\x80' + good[4:], good + b'extra'):
        with pytest.raises(p.ProbeError):
            p.parse_dns(bad, packet)


def test_dns_requires_address_for_queried_name_or_cname():
    packet = p.query('example.com')
    unrelated = answer(packet).replace(b'\xc0\x0c', b'\x05other\x03com\0')
    assert p.parse_dns(unrelated, packet)['state'] == 'error'
    target = b'\x05alias\x07example\x03com\0'
    cname = b'\xc0\x0c' + struct.pack('!HHIH', 5, 1, 60, len(target)) + target
    record = target + struct.pack('!HHIH', 1, 1, 60, 4) + b'\xc0\x00\x02\x02'
    response = packet[:2] + struct.pack('!5H', 0x8180, 1, 2, 0, 0) + packet[12:] + cname + record
    assert p.parse_dns(response, packet)['answers'] == ['192.0.2.2']
    nodata = packet[:2] + struct.pack('!5H', 0x8180, 1, 0, 0, 0) + packet[12:]
    assert p.parse_dns(nodata, packet)['state'] == 'error'


def fake_http(monkeypatch, *, status=200, content_type='application/dns-message', rcode=0):
    raw = Mock()
    raw.getpeercert.return_value = {'notAfter': 'Dec 31 23:59:59 2030 GMT'}
    raw.version.return_value = 'TLSv1.3'
    monkeypatch.setattr(p, 'public_ip', lambda *args: '192.0.2.1')
    monkeypatch.setattr(p.socket, 'create_connection', Mock(return_value=raw))
    context = Mock()
    context.wrap_socket.return_value = raw
    monkeypatch.setattr(p.ssl, 'create_default_context', lambda: context)
    response = Mock(status=status)
    response.getheader.return_value = content_type
    connection = Mock()
    connection.getresponse.return_value = response
    def request(*args, **kwargs):
        response.read1.side_effect = [answer(kwargs['body'], rcode), b'']
    connection.request.side_effect = request
    monkeypatch.setattr(p.http.client, 'HTTPConnection', Mock(return_value=connection))
    return connection, context


def test_successful_doh_verifies_tls_and_dns(monkeypatch):
    conn, context = fake_http(monkeypatch)
    result = p.checked('DoH', lambda: p.doh_check('https://example.com/dns-query', 'example.com'))
    assert result['state'] == 'healthy' and result['rcode'] == 'NOERROR'
    assert result['certificate_verified'] and result['certificate_expires']
    assert result['source'] == 'ssh' and result['elapsed_ms'] >= 0
    assert context.wrap_socket.call_args.kwargs['server_hostname'] == 'example.com'
    assert conn.request.call_args.args[:2] == ('POST', '/dns-query')
    conn.close.assert_called_once()


@pytest.mark.parametrize('options,reason', [({'content_type': 'text/html'}, 'doh_content_type'),
                                         ({'status': 302}, 'http_status'), ({'rcode': 2}, 'dns_rcode')])
def test_html_redirect_and_servfail_are_not_healthy(monkeypatch, options, reason):
    fake_http(monkeypatch, **options)
    result = p.checked('DoH', lambda: p.doh_check('https://example.com/dns-query', 'example.com'))
    assert result['state'] == 'error' and result['reason'] == reason


@pytest.mark.parametrize('error,reason,state', [(ssl.SSLCertVerificationError, 'certificate', 'error'),
    (TimeoutError, 'timeout', 'unavailable'), (PermissionError, 'permissions', 'unavailable'),
    (FileNotFoundError, 'missing_file', 'unconfigured'), (p.http.client.HTTPException, 'connection', 'unavailable')])
def test_exceptions_never_echo_secret_url(monkeypatch, caplog, error, reason, state):
    secret = 'https://example.com/' + uuid.uuid4().hex
    conn, context = fake_http(monkeypatch)
    conn.request.side_effect = error(secret)
    result = p.checked('DoH', lambda: p.doh_check(secret, 'example.com'))
    assert (result['reason'], result['state']) == (reason, state)
    assert secret not in json.dumps(result) + caplog.text


def unit(name, state='active'):
    return f'Id={name}.service\nLoadState=loaded\nActiveState={state}\n\n'


def discover(units='', docker='', unit_code=0, docker_code=0):
    return p.discover(lambda args: (unit_code, units) if args[0] == 'systemctl' else (docker_code, docker))


def test_adguard_image_not_container_name_and_stopped_discovery():
    role = discover(docker='custom-name\tadguard/adguardhome:v0.107.1\texited\t127.0.0.1:5300->53/udp\tadguard\n')[0]
    assert role['detected'] and role['state'] == 'stopped'
    assert role['functional'] == 'unconfigured'
    assert role['components'][0]['version'] == 'v0.107.1'
    assert '5300' in role['components'][0]['ports']
    assert not discover(docker='adguard\tother/image\trunning\t\tadguard')[0]['detected']


def test_permissions_are_unknown_not_missing():
    roles = discover(unit_code=1, docker_code=1)
    assert all(r['discovery'] == 'unavailable' for r in roles)
    assert discover(docker_code=1)[0]['discovery'] == 'unavailable'
    assert discover(unit('unbound'), unit_code=1)[1]['discovery'] == 'unavailable'


def test_secret_file_permission_and_symlink_fail_closed(monkeypatch):
    monkeypatch.setattr(p.os, 'lstat', Mock(side_effect=PermissionError))
    result = p.checked('Public DoH', lambda: p.doh_check(p.read_doh_url('/root/dns-doh-url'), 'example.com'))
    assert result['state'] == 'unavailable' and result['reason'] == 'permissions'
    monkeypatch.setattr(p.os, 'lstat', lambda path: Mock(st_mode=p.stat.S_IFLNK))
    with pytest.raises(p.ProbeError, match='configuration'):
        p.read_doh_url('/root/dns-doh-url')


def test_tcp_dns_framing_and_bounded_read(monkeypatch):
    packet = p.query('example.com')
    response = answer(packet)
    sock = Mock()
    sock.__enter__ = Mock(return_value=sock)
    sock.__exit__ = Mock(return_value=False)
    wire = bytearray(struct.pack('!H', len(response)) + response)
    def recv(size):
        part = bytes(wire[:min(size, 3)])
        del wire[:len(part)]
        return part
    sock.recv.side_effect = recv
    monkeypatch.setattr(p.socket, 'socket', lambda *args: sock)
    monkeypatch.setattr(p, 'query', lambda name: packet)
    assert p.dns_check('127.0.0.1', 5300, 'example.com', tcp=True)['state'] == 'healthy'
    sock.sendall.assert_called_once_with(struct.pack('!H', len(packet)) + packet)


def test_ordinary_mail_and_unbound_are_not_chatmail():
    for units in (unit('unbound'), unit('postfix') + unit('dovecot') + unit('unbound')):
        assert not any(r['detected'] for r in discover(units))


def test_chatmail_optional_units_do_not_determine_health():
    units = ''.join(unit(n) for n in p.CORE if n != 'postfix')
    role = discover(units, docker_code=127)[1]
    assert role['detected'] and role['state'] == 'running'
    assert any(r['optional'] and r['status'] == 'not_installed' for r in role['components'])
    partial = discover(units.replace('Id=dovecot.service\nLoadState=loaded\nActiveState=active',
                                    'Id=dovecot.service\nLoadState=loaded\nActiveState=failed'))[1]
    assert partial['state'] == 'partial'


@pytest.mark.parametrize('protocol,implicit,banner,commands', [
    ('smtp', False, b'220 ready\r\n250 STARTTLS\r\n220 go\r\n250 ready\r\n',
     [b'EHLO diagnostic.invalid\r\n', b'STARTTLS\r\n', b'EHLO diagnostic.invalid\r\n']),
    ('smtp', True, b'220 ready\r\n250 ready\r\n', [b'EHLO diagnostic.invalid\r\n']),
    ('imap', False, b'* OK ready\r\na1 OK begin TLS\r\n', [b'a1 STARTTLS\r\n']),
    ('imap', True, b'* OK ready\r\n', [])])
def test_mail_greeting_starttls_and_hostname_without_auth(monkeypatch, protocol, implicit, banner, commands):
    sock = Mock()
    sock.recv.side_effect = [bytes([b]) for b in banner]
    sock.getpeercert.return_value = {'notAfter': 'Dec 31 23:59:59 2030 GMT'}
    sock.version.return_value = 'TLSv1.3'
    monkeypatch.setattr(p.socket, 'create_connection', lambda *args, **kwargs: sock)
    context = Mock()
    context.wrap_socket.return_value = sock
    monkeypatch.setattr(p.ssl, 'create_default_context', lambda: context)
    result = p.mail_check('mail.example.com', '127.0.0.1', 993, protocol, implicit)
    assert result['state'] == 'healthy'
    assert [c.args[0] for c in sock.sendall.call_args_list] == commands
    context.wrap_socket.assert_called_once_with(sock, server_hostname='mail.example.com')


def test_unconfigured_mail_does_not_connect(monkeypatch):
    connect = Mock(side_effect=AssertionError('network forbidden'))
    monkeypatch.setattr(p.socket, 'create_connection', connect)
    results = p.diagnose(settings({'role': 'chatmail', 'turn_port': 0, 'iroh_port': 0}))
    assert len(results) == 5 and all(r['state'] == 'unconfigured' for r in results)
    connect.assert_not_called()


def test_turn_and_iroh_never_claim_full_functional_health(monkeypatch):
    sock = Mock()
    sock.__enter__ = Mock(return_value=sock)
    sock.__exit__ = Mock(return_value=False)
    transaction = bytes(range(12))
    monkeypatch.setattr(p.secrets, 'token_bytes', lambda length: transaction)
    sock.recv.return_value = struct.pack('!HHI', 0x101, 0, 0x2112a442) + transaction
    monkeypatch.setattr(p.socket, 'socket', lambda *args: sock)
    monkeypatch.setattr(p.socket, 'create_connection', lambda *args, **kwargs: sock)
    assert p.turn_check(3478) == {'state': 'partial', 'reason': 'stun_only'}
    assert p.iroh_check(3340) == {'state': 'partial', 'reason': 'tcp_only'}
    sock.recv.return_value = b'not a STUN reply'
    with pytest.raises(p.ProbeError):
        p.turn_check(3478)


def test_settings_reject_urls_and_bad_ports():
    for value in ({'doh_url': 'https://example.com'}, {'doh_file': 'https://example.com'},
                  {'doh_file': '/root/../file'}, {'dns_port': True}, {'smtp_port': 65536},
                  {'mail_domain': 'example.com/secret'}, {'role': []}):
        with pytest.raises((ValueError, TypeError)):
            settings(value)


def test_public_address_rejects_mixed_dns_answers(monkeypatch):
    monkeypatch.setattr(p.socket, 'getaddrinfo', lambda *args, **kwargs: [(0, 0, 0, '', ('1.1.1.1', 443)),
                                                                      (0, 0, 0, '', ('127.0.0.1', 443))])
    with pytest.raises(p.ProbeError, match='public_address'):
        p.public_ip('example.com', 443)


def test_ssh_payload_reads_secret_remotely_and_discards_stderr():
    client = Mock()
    stdin, stdout, stderr = Mock(), Mock(), Mock()
    stdout.read.return_value = b'[]'
    client.exec_command.return_value = stdin, stdout, stderr
    config = settings({})
    assert remote_probe(client, config) == []
    assert json.loads(stdin.write.call_args.args[0]) == config
    stderr.read.assert_not_called()
    stdout.channel.close.assert_called_once()
    assert 'https://' not in client.exec_command.call_args.args[0]


def test_discovery_failure_and_cached_result_staleness(monkeypatch):
    client = Mock()
    client.get_transport.return_value.getpeername.return_value = ('192.0.2.1', 22)
    monkeypatch.setattr('app.services.dns_mail.remote_probe', Mock(side_effect=PermissionError))
    assert all(row['role_summary']['discovery'] == 'unavailable' for row in discovery_rows(client))
    remember(client, settings({}), [{'name': 'DNS TCP', 'state': 'healthy', 'checked_at': p.timestamp()}])
    roles = [{'key': 'adguard'}]
    annotate(client, roles)
    assert roles[0]['last_check']['state'] == 'healthy' and not roles[0]['last_check']['stale']
    monkeypatch.setattr('app.services.dns_mail.time.monotonic', lambda: 10**15)
    annotate(client, roles)
    assert roles[0]['last_check']['stale']
