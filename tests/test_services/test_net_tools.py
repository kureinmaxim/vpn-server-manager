import io
import socket
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app.services.net_tools import ToolError, fetch_url, host_value, port_value, public_address, run_tool


@pytest.mark.parametrize('host', ['-n', 'a;whoami', 'https://example.com', 'a/b', 'a\nb', 'a b', '', None, [], 'x' * 64 + '.com'])
def test_bad_hosts(host):
    with pytest.raises(ToolError):
        host_value(host)


def test_idn_and_ipv6():
    assert host_value('пример.рф') == 'xn--e1afmkfd.xn--p1ai'
    assert host_value('2606:4700:4700::1111') == '2606:4700:4700::1111'


@pytest.mark.parametrize('port', [0, 65536, True, '22;id', '1.1', [], None])
def test_bad_ports(port):
    with pytest.raises(ToolError):
        port_value(port)


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1', '192.0.2.1'])
def test_non_public_and_mixed_dns_answers_are_blocked(ip):
    entries = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443)),
               (socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]
    with patch('socket.getaddrinfo', return_value=entries), pytest.raises(ToolError, match='public'):
        public_address('example.com', 443)


def test_dns_ptr_uses_reverse_name():
    with patch('app.services.net_tools.provider_json', return_value={'Status': 0}) as provider:
        assert run_tool('dns', {'host': '8.8.8.8', 'record': 'PTR'}) == {'Status': 0}
    provider.assert_called_once_with('https://dns.google/resolve', {'name': '8.8.8.8.in-addr.arpa', 'type': 'PTR'})


def test_port_uses_validated_ip():
    with patch('app.services.net_tools.public_address', return_value='8.8.8.8'), patch('socket.create_connection') as connect:
        assert run_tool('port', {'host': 'example.com', 'port': '443'})['reachable'] is True
        connect.assert_called_once_with(('8.8.8.8', 443), timeout=5)
        connect.side_effect = ConnectionRefusedError
        assert run_tool('port', {'host': 'example.com', 'port': 443})['reachable'] is False


def test_ping_has_no_shell_and_is_bounded():
    with patch('app.services.net_tools.public_address', return_value='8.8.8.8'), patch('subprocess.run') as process:
        process.return_value = subprocess.CompletedProcess([], 1, b'no reply', b'')
        result = run_tool('ping', {'host': 'example.com'})
        assert result['exit_code'] == 1
        assert process.call_args.args[0][-1] == '8.8.8.8'
        assert process.call_args.kwargs['timeout'] == 20
        assert not process.call_args.kwargs.get('shell')


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'ftp://example.com', 'http://user:pw@example.com', 'http://example.com\r\nX: y', 'http://example.com:99999', 'http://', [], 'http://[::1'])
def test_invalid_urls(url):
    with pytest.raises(ToolError):
        fetch_url(url)


def test_fetch_is_pinned_truncated_and_does_not_follow_redirects():
    response = MagicMock(status=302, reason='Found')
    response.getheaders.return_value = [('Location', 'http://127.0.0.1/'), ('Content-Type', 'text/html')]
    body = io.BytesIO(b'<script>alert(1)</script>' + b'x' * 70000)
    response.read1.side_effect = body.read1
    connection = MagicMock()
    connection.getresponse.return_value = response
    with patch('app.services.net_tools.public_address', return_value='8.8.8.8') as resolve, \
         patch('socket.create_connection') as connect, \
         patch('http.client.HTTPConnection', return_value=connection):
        result = fetch_url('http://example.com/test?q=1')
    resolve.assert_called_once_with('example.com', 80)
    connect.assert_called_once_with(('8.8.8.8', 80), timeout=5)
    assert result['truncated'] is True
    assert len(result['body']) == 65536
    assert result['status'] == 302
    assert result['headers']['location'] == 'http://127.0.0.1/'
    assert connection.request.call_args.args == ('GET', '/test?q=1')
    connection.close.assert_called_once()


def test_tls_verifies_hostname():
    with patch('app.services.net_tools.public_address', return_value='8.8.8.8'), \
         patch('socket.create_connection'), patch('ssl.create_default_context') as context:
        run_tool('tls', {'host': 'example.com', 'port': 443})
        assert context.return_value.wrap_socket.call_args.kwargs['server_hostname'] == 'example.com'


def test_rdap_redirect_and_json():
    with patch('app.services.net_tools.fetch_url', side_effect=[
        {'status': 302, 'headers': {'location': 'https://registry.example/domain/example.com'}},
        {'status': 200, 'body': '{"objectClassName":"domain"}'}
    ]) as fetch:
        assert run_tool('whois', {'host': 'example.com'}) == {'objectClassName': 'domain'}
        assert fetch.call_count == 2


def test_rdap_rejects_https_downgrade():
    with patch('app.services.net_tools.fetch_url', return_value={'status': 302, 'headers': {'location': 'http://registry.example'}}):
        with pytest.raises(ToolError):
            run_tool('whois', {'host': 'example.com'})


def test_location_and_my_ip_providers():
    with patch('app.services.net_tools.public_address', return_value='8.8.8.8'), \
         patch('app.services.net_tools.provider_json', return_value={'ip': '8.8.8.8'}) as provider:
        run_tool('location', {'host': 'example.com'})
        provider.assert_called_with('https://ipinfo.io/8.8.8.8/json')
        run_tool('my-ip', {})
        provider.assert_called_with('https://ipinfo.io/json')
