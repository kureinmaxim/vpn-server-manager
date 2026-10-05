import json

import pytest

from app.services.hysteria_mutations import parse_hysteria
from app.services.protocol_mutations import changed_protocol


YAML = b'''# TelegramOnly-style configuration
listen: ":443"
tls:
  cert: "/etc/hysteria/server.crt"
  key: "/etc/hysteria/server.key"
auth:
  type: "userpass"
  userpass:
    alice: "fixture-one"
    bob: "fixture-two"
quic:
  disablePathMTUDiscovery: true
  maxIdleTimeout: "30s"
'''


def config():
    return {'port':443, 'clients':[{'name':'alice','password':'fixture-one'}, {'name':'bob','password':'fixture-two'}]}


def test_yaml_port_preserves_other_settings_and_roundtrips():
    runtime = parse_hysteria(YAML)
    manager, changed = changed_protocol('hysteria2', config(), runtime, {'kind':'port','port':8443})
    assert changed['listen'] == ':8443' and manager['port'] == 8443
    assert changed['quic'] == runtime['quic'] and changed['tls'] == runtime['tls']
    assert parse_hysteria(json.dumps(changed).encode()) == changed
    assert runtime['listen'] == ':443'


def test_yaml_revoke_and_last_client():
    manager, runtime = changed_protocol('hysteria2', config(), parse_hysteria(YAML), {'kind':'remove_client','name':'alice'})
    assert runtime['auth']['userpass'] == {'bob':'fixture-two'}
    with pytest.raises(ValueError, match='last_client'):
        changed_protocol('hysteria2', manager, runtime, {'kind':'remove_client','name':'bob'})


def test_legacy_password_only_allows_port_changes():
    manager = {'port':443,'password':'fixture-shared','clients':[]}
    runtime = parse_hysteria(YAML); runtime['auth'] = {'type':'password','password':'fixture-shared'}
    updated, live = changed_protocol('hysteria2', manager, runtime, {'kind':'port','port':8443})
    assert live['auth'] == runtime['auth'] and updated['clients'] == []
    with pytest.raises(ValueError, match='shared_password'):
        changed_protocol('hysteria2', manager, runtime, {'kind':'add_client','name':'alice'})


def test_default_client_cannot_be_restored_from_root_password():
    manager, runtime = config(), parse_hysteria(YAML)
    manager['password'] = 'fixture-one'
    with pytest.raises(ValueError, match='config_mismatch'):
        changed_protocol('hysteria2', manager, runtime, {'kind':'port','port':8443})
    manager['clients'][0]['name'] = 'default'
    runtime['auth']['userpass']['default'] = runtime['auth']['userpass'].pop('alice')
    with pytest.raises(ValueError, match='protected_client'):
        changed_protocol('hysteria2', manager, runtime, {'kind':'remove_client','name':'default'})


@pytest.mark.parametrize('name', ['Alice', 'a.b'])
def test_names_with_ambiguous_viper_mapping_are_rejected(name):
    with pytest.raises(ValueError, match='invalid_change'):
        changed_protocol('hysteria2', config(), parse_hysteria(YAML), {'kind':'add_client','name':name})


@pytest.mark.parametrize('raw', [b'a: 1\na: 2', b'a: 1\nA: 2', b'a: &ref {}', b'a: *ref',
    b'a: !!python/object:x {}', b'a: |\n  text', b'a:\n - item', b'a: yes', b'a: False', b'a: TRUE', b'a: 012',
    b'a: 1 # comment', b'a:\n    b: 2', b'a:\n\tb: 2', b'{"a":1,"a":2}', b'{"a":1,"A":2}'])
def test_ambiguous_yaml_is_rejected(raw):
    with pytest.raises(ValueError): parse_hysteria(raw)


@pytest.mark.parametrize('field', ['auth', 'tls', 'listen', 'obfs', 'acme'])
def test_live_mismatch_blocks_change(field):
    runtime = parse_hysteria(YAML)
    runtime[field] = {'unexpected':True}
    with pytest.raises(ValueError):
        changed_protocol('hysteria2', config(), runtime, {'kind':'port','port':8443})
