from urllib.parse import parse_qs, unquote, urlsplit

import pytest
from app.services import protocol_clients as profiles

UUID = '12345678-1234-1234-1234-123456789abc'


def test_hysteria_userpass_and_obfuscation():
    config = dict(server='2001:db8::1', clients=[{}], sni='example.com',
                  obfs_type='salamander', obfs_password='a&b', insecure=True)
    uri = urlsplit(profiles.export_profile('hysteria2', config, {'name': 'a:b', 'password': 'p@ss/?'}))
    assert unquote(uri.username) == 'a:b'
    assert unquote(uri.password) == 'p@ss/?'
    assert uri.hostname == '2001:db8::1'
    assert parse_qs(uri.query)['obfs-password'] == ['a&b']


def test_hysteria_legacy_password_only():
    uri = urlsplit(profiles.export_profile('hysteria2', {'server': 'example.com'}, {'password': 'fixture'}))
    assert uri.username == 'fixture' and uri.password is None


def test_vless_reality_parameters():
    uri = urlsplit(profiles.export_profile('vless', dict(server='example.com', public_key='a'*43,
                  short_id='abcd', sni='example.org'), {'uuid': UUID}))
    query = parse_qs(uri.query)
    assert query['security'] == ['reality'] and query['pbk'] == ['a'*43]
    assert query['sid'] == ['abcd'] and uri.username == UUID


def test_vless_rejects_incompatible_transport():
    with pytest.raises(ValueError, match='unsupported_profile'):
        profiles.export_profile('vless', dict(server='example.com', transport='grpc'), {'uuid': UUID})


def test_naive_domain_and_shared_account(monkeypatch):
    data = dict(domain='example.com', server='192.0.2.1', username='name@domain', password='p:?#')
    monkeypatch.setattr(profiles, 'sources', lambda *a: {'naiveproxy': [('/fixture', 'candidate')]})
    monkeypatch.setattr(profiles, 'read_metadata', lambda *a: (data, 'revision'))
    body = dict(component='naiveproxy', source_id=profiles.source_id('/fixture'), revision='revision', operation='clients')
    result = profiles.client_operation(body, {}, None)
    assert result['clients'] == [{'index': 0, 'name': 'name@domain', 'exportable': True}]
    assert 'password' not in str(result)
    result = profiles.client_operation(dict(body, operation='export_client', index=0), {}, None)
    uri = urlsplit(result['profile'])
    assert uri.hostname == 'example.com' and uri.scheme == 'naive+https'
    assert unquote(uri.password) == 'p:?#'


def test_mieru_preserves_repeated_bindings():
    uri = urlsplit(profiles.export_profile('mieru', dict(server='example.com', port_bindings=[
        {'port': 1234, 'protocol': 'TCP'}, {'port': 4321, 'protocol': 'UDP'}]),
        {'name': 'client', 'password': 'fixture'}))
    query = parse_qs(uri.query)
    assert query['port'] == ['1234', '4321']
    assert query['protocol'] == ['TCP', 'UDP']


@pytest.mark.parametrize('span', [{'from': 2000, 'to': 2100}, '2000-2100'])
def test_mieru_ranges(span):
    uri = profiles.export_profile('mieru', dict(server='example.com', port_bindings=[
        {'portRange': span, 'protocol': 'TCP'}]), {'name': 'test', 'password': 'fixture'})
    assert parse_qs(urlsplit(uri).query)['port'] == ['2000-2100']


@pytest.mark.parametrize('kind,config,client', [
    ('vless', {'public_key': 'bad'}, {'uuid': UUID}),
    ('hysteria2', {'obfs_type': 'unsupported'}, {'password': 'fixture'}),
    ('naiveproxy', {'scheme': 'file'}, {}),
    ('mieru', {'port_bindings': [{'port': True, 'protocol': 'TCP'}]}, {'name': 'test', 'password': 'fixture'}),
])
def test_invalid_profiles_fail_closed(kind, config, client):
    with pytest.raises(ValueError):
        profiles.export_profile(kind, dict(config, server='example.com'), client)
