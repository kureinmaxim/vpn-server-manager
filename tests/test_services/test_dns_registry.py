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


@pytest.mark.parametrize('name,rtype,expected', [
    ('@', 'A', 'main'), ('vpn', 'A', 'main'), ('www', 'CNAME', 'main'), ('headscale', 'A', 'main'),
    ('@', 'MX', 'service'), ('@', 'TXT', 'service'), ('_dmarc', 'TXT', 'service'),
    ('_domainconnect', 'CNAME', 'service'), ('default._domainkey', 'TXT', 'service'),
    ('_caldav._tcp', 'SRV', 'service'), ('webmail', 'A', 'service'), ('cpcontacts', 'A', 'service'),
    ('mail', 'CNAME', 'service'),
])
def test_auto_role(name, rtype, expected):
    assert dns_reg.role({'name': name, 'type': rtype}) == expected


def test_manual_role_overrides_and_hides_from_host_choices():
    domain = {'name': 'example.com'}
    record = dns_reg.build_record({'name': 'ftp', 'type': 'A', 'content': '1.2.3.4', 'role': 'main'}, domain)
    assert dns_reg.role(record) == 'main'
    hidden = dns_reg.build_record({'name': 'nas', 'type': 'A', 'content': '100.64.0.12', 'role': 'service'}, domain)
    dns = {'domains': [dict(domain, id='d', records=[record, hidden])]}
    assert dns_reg.host_choices(dns) == ['example.com', 'ftp.example.com']
    assert dns_reg.address_scope(hidden) == 'private' and dns_reg.address_scope(record) == ''
    assert dns_reg.build_record({'type': 'A', 'content': '1.2.3.4'}, domain, record)['role'] == 'main'


def test_records_for_ip_and_move():
    domain = {'id': 'd', 'name': 'kurein.me', 'records': []}
    for name, rtype, content in [('@', 'A', '138.124.71.73'), ('vpn', 'A', '138.124.71.73'),
                                 ('hip', 'A', '192.0.2.1'), ('www', 'CNAME', 'kurein.me'),
                                 ('_dmarc', 'TXT', '138.124.71.73')]:
        domain['records'].append(dns_reg.build_record({'name': name, 'type': rtype, 'content': content}, domain))
    dns = {'domains': [domain]}
    items = dns_reg.records_for_ip(dns, '138.124.71.73')
    assert [(i['fqdn'], i['via']) for i in items] == [
        ('kurein.me', None), ('vpn.kurein.me', None), ('www.kurein.me', 'kurein.me')]
    vpn = next(i['record'] for i in items if i['fqdn'] == 'vpn.kurein.me')
    assert dns_reg.move_records(dns, '138.124.71.73', '203.0.113.9', {vpn['id']}) == 1
    assert vpn['content'] == '203.0.113.9'
    assert dns_reg.move_records(dns, '138.124.71.73', '2001:db8::1', {i['record']['id'] for i in items}) == 0
    assert dns_reg.records_for_ip(dns, '') == []


ZONE = """;; Domain:     example.com.
example.com	3600	IN	SOA	cora.ns.cloudflare.com. dns.cloudflare.com. 1 10000 2400 604800 3600
example.com.	86400	IN	NS	cora.ns.cloudflare.com.
vpn.example.com.	1	IN	A	203.0.113.5 ; cf_tags=cf-proxied:false
example.com.	1	IN	A	203.0.113.5 ; cf_tags=cf-proxied:true
www.example.com.	1	IN	CNAME	example.com. ; cf_tags=cf-proxied:true
example.com.	1	IN	MX	0 example.com.
_caldav._tcp.example.com.	1	IN	SRV	0 0 2079 example.com.
_dmarc.example.com.	1	IN	TXT	"v=DMARC1; p=quarantine; rua=mailto:a@b.net;"
default._domainkey.example.com.	1	IN	TXT	"v=DKIM1; p=AAA" "BBB;"
bad name.example.com.	1	IN	A	203.0.113.5
"""


def test_parse_zone():
    assert dns_reg.zone_domain(ZONE) == 'example.com'
    domain = {'name': 'example.com', 'records': []}
    records, skipped = dns_reg.parse_zone(ZONE, domain)
    got = {(r['name'], r['type']): (r['content'], r['proxied']) for r in records}
    assert got == {
        ('vpn', 'A'): ('203.0.113.5', False), ('@', 'A'): ('203.0.113.5', True),
        ('www', 'CNAME'): ('example.com', True), ('@', 'MX'): ('0 example.com', False),
        ('_caldav._tcp', 'SRV'): ('0 0 2079 example.com', False),
        ('_dmarc', 'TXT'): ('v=DMARC1; p=quarantine; rua=mailto:a@b.net;', False),
        ('default._domainkey', 'TXT'): ('v=DKIM1; p=AAABBB;', False)}
    assert skipped == 1
    assert dns_reg.add_zone_records(domain, records) == 7
    assert dns_reg.add_zone_records(domain, dns_reg.parse_zone(ZONE, domain)[0]) == 0
    with pytest.raises(dns_reg.DnsError):
        dns_reg.zone_domain('just text')
