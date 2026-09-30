import datetime
import json

import pytest
from cryptography.fernet import Fernet

from app.services import dns_registry as dns_reg
from app.services.data_manager_service import DataManagerService


@pytest.fixture
def manager(tmp_path):
    return DataManagerService(Fernet.generate_key().decode(), str(tmp_path))


def raw(manager, path):
    return json.loads(manager.fernet.decrypt(path.read_bytes()))


def test_file_stays_legacy_list_without_dns(manager, tmp_path):
    path = tmp_path / 'servers.enc'
    manager.save_servers([{'id': 1, 'name': 'a'}], str(path))
    assert isinstance(raw(manager, path), list)


def test_saving_servers_keeps_dns_and_saving_dns_keeps_servers(manager, tmp_path):
    path = tmp_path / 'servers.enc'
    config = {'active_data_file': str(path)}
    manager.save_servers([{'id': 1, 'name': 'a'}], str(path))
    dns = {'providers': [], 'domains': [{'id': 'd1', 'name': 'example.com', 'records': []}]}
    manager.save_dns(dns, str(path))
    assert raw(manager, path)['dns'] == dns

    servers = manager.load_servers(config)
    servers.append({'id': 2, 'name': 'b'})
    manager.save_servers(servers, str(path))
    assert [s['name'] for s in manager.load_servers(config)] == ['a', 'b']
    assert manager.load_dns(config) == dns

    manager.save_dns({}, str(path))
    assert isinstance(raw(manager, path), list)


def test_verify_key_accepts_new_format(manager, tmp_path):
    path = tmp_path / 'servers.enc'
    manager.save_servers([{'id': 1, 'name': 'a', 'provider': 'p'}], str(path),
                         dns={'providers': [], 'domains': [{'id': 'd', 'name': 'x.io', 'records': []}]})
    result = manager.verify_key_for_file(path.read_bytes(), manager.secret_key)
    assert result['success'] and result['server_count'] == 1 and result['dns_domain_count'] == 1


def test_provider_secrets_are_encrypted_and_kept_when_blank(manager):
    provider = dns_reg.build_provider({'kind': 'cloudflare', 'user': 'me@x.io', 'password': 'p%ss'}, None,
                                      manager.encrypt_data)
    assert provider['name'] == 'Cloudflare' and provider['login_url'].startswith('https://dash.cloudflare.com')
    assert provider['password'].startswith('gAAAAA') and manager.decrypt_data(provider['password']) == 'p%ss'
    edited = dns_reg.build_provider({'kind': 'cloudflare', 'name': 'CF'}, provider, manager.encrypt_data)
    assert edited['password'] == provider['password']
    cleared = dns_reg.build_provider({'kind': 'cloudflare', 'clear_password': '1'}, provider, manager.encrypt_data)
    assert cleared['password'] == ''


@pytest.mark.parametrize('value', ['localhost', 'http://x.com', 'a..com', '-a.com', 'x' * 64 + '.com'])
def test_bad_domains_rejected(value):
    with pytest.raises(dns_reg.DnsError):
        dns_reg.clean_domain(value)


def test_idn_domain_is_stored_as_punycode():
    assert dns_reg.clean_domain('Пример.РФ') == 'xn--e1afmkfd.xn--p1ai'


def test_record_names_and_values():
    domain = {'name': 'example.com'}
    assert dns_reg.build_record({'name': 'vpn.example.com', 'type': 'a', 'content': '1.2.3.4'}, domain)['name'] == 'vpn'
    assert dns_reg.build_record({'name': '', 'type': 'TXT', 'content': 'v=spf1', 'proxied': 'on'}, domain) \
        ['name'] == '@'
    assert dns_reg.build_record({'name': '*', 'type': 'CNAME', 'content': 'example.com'}, domain)['name'] == '*'
    txt = dns_reg.build_record({'name': '_dmarc', 'type': 'TXT', 'content': 'v=DMARC1', 'proxied': 'on'}, domain)
    assert txt['proxied'] is False
    for bad in ({'type': 'A', 'content': '::1'}, {'type': 'AAAA', 'content': '1.2.3.4'},
                {'type': 'BOGUS', 'content': 'x'}, {'type': 'A', 'content': ''},
                {'name': 'bad name', 'type': 'A', 'content': '1.2.3.4'}):
        with pytest.raises(dns_reg.DnsError):
            dns_reg.build_record(bad, domain)


def test_host_choices_and_days_left():
    dns = {'domains': [{'id': 'd', 'name': 'example.com', 'records': [
        {'id': '1', 'name': '@', 'type': 'A', 'content': '1.1.1.1'},
        {'id': '2', 'name': 'vpn', 'type': 'A', 'content': '1.1.1.1'},
        {'id': '3', 'name': '*', 'type': 'CNAME', 'content': 'example.com'}]}]}
    assert dns_reg.host_choices(dns) == ['example.com', 'vpn.example.com']
    today = datetime.date(2026, 9, 30)
    assert dns_reg.days_left({'expires_on': '2026-10-10'}, today) == 10
    assert dns_reg.days_left({'expires_on': ''}, today) is None


def test_merge_reencrypts_and_remaps_providers():
    current = {'providers': [{'id': 'p1', 'name': 'Cloudflare'}], 'domains': [{'id': 'd1', 'name': 'a.com'}]}
    incoming = {'providers': [{'id': 'x1', 'name': 'cloudflare', 'password': 'old'},
                              {'id': 'x2', 'name': 'Porkbun', 'password': 'old'}],
                'domains': [{'id': 'e1', 'name': 'a.com', 'provider_id': 'x1'},
                            {'id': 'e2', 'name': 'b.com', 'provider_id': 'x1'},
                            {'id': 'e3', 'name': 'c.com', 'provider_id': 'x2'}]}
    merged, added = dns_reg.merge(current, incoming, lambda value: 'new-' + value)
    assert added == 2
    porkbun = merged['providers'][1]
    assert porkbun['password'] == 'new-old' and porkbun['id'] != 'x2'
    by_name = {d['name']: d for d in merged['domains']}
    assert by_name['b.com']['provider_id'] == 'p1' and by_name['c.com']['provider_id'] == porkbun['id']
