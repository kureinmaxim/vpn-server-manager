import pytest

from app.services.ssh_config_import import SSHConfigImportError, parse_ssh_config


def test_imports_global_defaults_and_exact_host_values(tmp_path):
    result = parse_ssh_config('''
User operator
Port 2207
Host edge
  HostName 192.0.2.17
  IdentityFile ~/.ssh/edge_key
  HostKeyAlias edge-key
Host edge-copy
  HostName edge.example.test
''', home=tmp_path)

    assert result['hosts'] == [
        {'alias': 'edge', 'host_name': '192.0.2.17', 'user': 'operator', 'port': 2207,
         'identity_file': str(tmp_path / '.ssh' / 'edge_key'), 'unsupported': ['line 7: HostKeyAlias']},
        {'alias': 'edge-copy', 'host_name': 'edge.example.test', 'user': 'operator', 'port': 2207,
         'identity_file': None, 'unsupported': []},
    ]
    assert result['unsupported'] == []


def test_reports_unsupported_without_returning_values_or_comments(tmp_path):
    result = parse_ssh_config('''
# private comment with secret-marker
Host bastion
  HostName 192.0.2.30
  ProxyJump hidden-hop
  ProxyCommand echo sensitive-command
  IdentityFile ~/.ssh/one
  IdentityFile ~/.ssh/two
Host *.example.test
  User wildcard-user
Include ~/.ssh/private.conf
Match host special
  HostName 192.0.2.31
''', home=tmp_path)

    assert [host['alias'] for host in result['hosts']] == ['bastion']
    assert result['hosts'][0]['identity_file'] == str(tmp_path / '.ssh' / 'one')
    assert any('ProxyJump' in item for item in result['hosts'][0]['unsupported'])
    assert any('ProxyCommand' in item for item in result['hosts'][0]['unsupported'])
    assert any('Host pattern' in item for item in result['unsupported'])
    assert any('Include' in item for item in result['unsupported'])
    assert any('Match' in item for item in result['unsupported'])
    serialized = repr(result)
    for private in ('hidden-hop', 'sensitive-command', 'secret-marker', 'wildcard-user', 'private.conf'):
        assert private not in serialized


@pytest.mark.parametrize('text', [
    'Host bad/name\n  HostName invalid host\n  Port 99999\n',
    'Host bad\n  HostName %h\n  IdentityFile ~/.ssh/key-%n\n',
])
def test_invalid_or_tokenized_values_are_not_imported(text):
    result = parse_ssh_config(text, home='/tmp/profile')
    if 'bad/name' in text:
        assert result['hosts'] == []
        assert any('Host alias' in item for item in result['unsupported'])
    else:
        assert result['hosts'][0]['host_name'] == 'bad'
        assert result['hosts'][0]['identity_file'] is None
        assert any('HostName value' in item for item in result['hosts'][0]['unsupported'])
        assert any('IdentityFile value' in item for item in result['hosts'][0]['unsupported'])


def test_accepts_ipv6_and_ignores_invalid_ports():
    result = parse_ssh_config('Host local-v6\n HostName ::1\n Port 0\n')
    assert result['hosts'][0]['host_name'] == '::1'
    assert result['hosts'][0]['port'] == 22
    assert result['hosts'][0]['unsupported'] == ['line 3: Port value']


def test_limits_config_size():
    with pytest.raises(SSHConfigImportError):
        parse_ssh_config('x' * (1024 * 1024 + 1))
