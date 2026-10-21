import re

import pytest
from cryptography.fernet import Fernet

from app.services import registry
from app.services.data_manager_service import DataManagerService


@pytest.fixture
def unlocked(app, client, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = tmp_path / 'servers.enc'
    manager.save_servers([{'id': 1, 'name': 'vps', 'ip_address': '192.0.2.10'},
                          {'id': 2, 'name': 'new', 'ip_address': '203.0.113.9'}], str(path))
    registry.register('data_manager', manager)
    app.config['active_data_file'] = str(path)
    with client.session_transaction() as session:
        session['pin_authenticated'] = True
        session['csrf_token'] = 'token'
    client.manager = manager
    return client


def post(client, url, **data):
    return client.post(url, data=dict(data, csrf_token='token'))


def dns(client):
    return client.manager.load_dns({'active_data_file': client.application.config['active_data_file']})


def test_locked(client):
    assert client.get('/dns/').status_code == 302


def test_csrf_required(unlocked):
    unlocked.post('/dns/domains/new', data={'name': 'example.com'})
    assert dns(unlocked) == {}


def test_provider_domain_record_flow(unlocked):
    assert post(unlocked, '/dns/providers/new', kind='cloudflare', user='me@example.com',
                password='s3cr%t').status_code == 302
    provider = dns(unlocked)['providers'][0]
    assert provider['password'] != 's3cr%t'
    page = unlocked.get('/dns/').text
    assert 'https://dash.cloudflare.com/login' in page and 'me@example.com' in page

    post(unlocked, '/dns/domains/new', name='Example.com', provider_id=provider['id'],
         registrar='Namecheap', expires_on='2027-01-02')
    domain = dns(unlocked)['domains'][0]
    assert domain['name'] == 'example.com' and domain['registrar'] == 'Namecheap'
    assert post(unlocked, '/dns/domains/new', name='example.com').status_code == 200
    assert len(dns(unlocked)['domains']) == 1

    post(unlocked, f"/dns/domains/{domain['id']}/records", name='vpn', type='A', content='203.0.113.5')
    record = dns(unlocked)['domains'][0]['records'][0]
    assert 'vpn.example.com' in unlocked.get(f"/dns/domains/{domain['id']}").text

    tool = unlocked.get('/net-tools/port').text
    assert '<option value="vpn.example.com">' in tool and 'net-saved' in tool

    post(unlocked, f"/dns/domains/{domain['id']}/records/{record['id']}", name='vpn', type='A', content='203.0.113.6')
    assert dns(unlocked)['domains'][0]['records'][0]['content'] == '203.0.113.6'
    post(unlocked, f"/dns/domains/{domain['id']}/records/{record['id']}/delete")
    assert dns(unlocked)['domains'][0]['records'] == []

    post(unlocked, f"/dns/providers/{provider['id']}/delete")
    assert dns(unlocked)['domains'][0]['provider_id'] == ''
    post(unlocked, f"/dns/domains/{domain['id']}/delete")
    assert dns(unlocked) == {}
    assert unlocked.manager.load_servers({'active_data_file': unlocked.application.config['active_data_file']})[0]['name'] == 'vps'


def test_index_has_dns_button(unlocked):
    assert 'btn-dns' in unlocked.get('/').text


def test_own_dns_guide_is_translated(unlocked):
    page = unlocked.get('/dns/?lang=en').text
    assert 'Own DNS server' in page and 'id="own-tab-openwrt"' in page
    assert 'roles-snapshot' in page and 'js/dns_own.js' in page
    assert 'Never give guests the DoH address' in page and 'id="own-doh-url"' in page
    assert 'data-own-wrt="ssclash"' in page and 'data-own-wrt="podkop"' in page
    assert 'data-own-wrt="forkop"' in page and 'data-own-wrt="zapret"' in page
    config = page.split('window.OWN_DNS = ')[1].split('</script>')[0]
    assert 'hosts: {}' in config
    assert 'password' not in config and 'private_key' not in config
    assert 'Devices connect through your DoH address' in config
    assert not re.search('[А-Яа-яЁё]', config)


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_pages_localized(unlocked, lang):
    unlocked.get('/dns/?lang=' + lang)
    post(unlocked, '/dns/providers/new', kind='cloudflare')
    post(unlocked, '/dns/domains/new', name='example.com', expires_on='2020-01-01')
    domain_id = dns(unlocked)['domains'][0]['id']
    for url in ('/dns/', '/dns/providers/new', '/dns/domains/new', f'/dns/domains/{domain_id}',
                f"/dns/providers/{dns(unlocked)['providers'][0]['id']}/edit"):
        text = unlocked.get(url).text
        section = text.split('<div class="container dns-page')[1].split('</main>')[0]
        # Flash messages from the POSTs above are also localized
        assert not re.search('[А-Яа-яЁё]', section), url


def test_service_records_are_grouped_and_toggle(unlocked):
    post(unlocked, '/dns/domains/new', name='example.com')
    domain_id = dns(unlocked)['domains'][0]['id']
    post(unlocked, f'/dns/domains/{domain_id}/records', name='vpn', type='A', content='203.0.113.5')
    post(unlocked, f'/dns/domains/{domain_id}/records', name='webmail', type='A', content='203.0.113.5')
    page = unlocked.get(f'/dns/domains/{domain_id}').text
    main, service = page.split('class="dns-service')
    assert 'vpn.example.com' in main and 'webmail.example.com' not in main and 'webmail.example.com' in service

    webmail = next(r for r in dns(unlocked)['domains'][0]['records'] if r['name'] == 'webmail')
    post(unlocked, f"/dns/domains/{domain_id}/records/{webmail['id']}/role")
    assert next(r for r in dns(unlocked)['domains'][0]['records'] if r['name'] == 'webmail')['role'] == 'main'
    assert 'webmail.example.com' in unlocked.get('/net-tools/port').text
    post(unlocked, f"/dns/domains/{domain_id}/records/{webmail['id']}/role")
    assert next(r for r in dns(unlocked)['domains'][0]['records'] if r['name'] == 'webmail')['role'] == 'auto'


def test_server_card_lists_dns_and_moves_records(unlocked):
    post(unlocked, '/dns/domains/new', name='example.net')
    domain_id = dns(unlocked)['domains'][0]['id']
    for name, rtype, content in [('@', 'A', '192.0.2.10'), ('vpn', 'A', '192.0.2.10'), ('www', 'CNAME', 'example.net')]:
        post(unlocked, f'/dns/domains/{domain_id}/records', name=name, type=rtype, content=content)
    index = unlocked.get('/').text
    assert 'collapse-dns-1' in index and 'vpn.example.net' in index and 'collapse-dns-2' not in index

    page = unlocked.get('/dns/move/1?to=2').text
    assert '203.0.113.9' in page and 'www.example.net' in page
    vpn = next(r for r in dns(unlocked)['domains'][0]['records'] if r['name'] == 'vpn')
    response = unlocked.post('/dns/move/1', data={'csrf_token': 'token', 'to': '2', 'record': [vpn['id']]})
    assert response.status_code == 302 and response.headers['Location'].endswith('/dns/move/2')
    contents = {r['name']: r['content'] for r in dns(unlocked)['domains'][0]['records']}
    assert contents == {'@': '192.0.2.10', 'vpn': '203.0.113.9', 'www': 'example.net'}
    assert unlocked.get('/dns/move/99').status_code == 404


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_move_page_localized(unlocked, lang):
    unlocked.get('/?lang=' + lang)
    post(unlocked, '/dns/domains/new', name='example.net')
    domain_id = dns(unlocked)['domains'][0]['id']
    post(unlocked, f'/dns/domains/{domain_id}/records', name='vpn', type='A', content='192.0.2.10')
    text = unlocked.get('/dns/move/1?to=2').text
    section = text.split('<div class="container dns-page')[1].split('</main>')[0]
    assert not re.search('[А-Яа-яЁё]', section)


def test_import_zone_files(unlocked):
    import io
    from tests.test_services.test_dns_registry import ZONE
    post(unlocked, '/dns/providers/new', kind='cloudflare')
    for _ in range(2):
        response = unlocked.post('/dns/import-zone', data={
            'csrf_token': 'token', 'provider_id': dns(unlocked)['providers'][0]['id'],
            'zone': [(io.BytesIO(ZONE.encode()), 'example.com.txt'), (io.BytesIO(b'junk'), 'x.txt')]},
            content_type='multipart/form-data', follow_redirects=True)
    data = dns(unlocked)
    assert len(data['domains']) == 1 and len(data['domains'][0]['records']) == 7
    assert data['domains'][0]['provider_id'] == data['providers'][0]['id']
    assert '0 records added, 7 already present' in response.text


def test_import_zone_replace(unlocked):
    import io
    from tests.test_services.test_dns_registry import ZONE
    post(unlocked, '/dns/providers/new', kind='cloudflare')
    provider_id = dns(unlocked)['providers'][0]['id']

    def upload(text, mode):
        return unlocked.post('/dns/import-zone', data={
            'csrf_token': 'token', 'provider_id': provider_id, 'mode': mode,
            'zone': [(io.BytesIO(text.encode()), 'zone.txt')]},
            content_type='multipart/form-data', follow_redirects=True)

    assert 'zone-mode-replace' in unlocked.get('/dns/').text
    clean = '\n'.join(line for line in ZONE.splitlines() if not line.startswith('bad name')) + '\n'
    upload(clean, 'add')
    domain_id = dns(unlocked)['domains'][0]['id']
    post(unlocked, f'/dns/domains/{domain_id}/edit', name='example.com', provider_id=provider_id,
         registrar='Example Registrar', registered_on='2026-07-30', expires_on='2027-07-30')
    zone = (";; Domain:     example.com.\n"
            "files.example.com.\t1\tIN\tA\t203.0.113.7 ; cf_tags=cf-proxied:false\n"
            'example.com.\t1\tIN\tTXT\t"v=spf1 -all"\n')
    response = upload(zone, 'replace')
    domain = dns(unlocked)['domains'][0]
    assert {(r['name'], r['type']) for r in domain['records']} == {('files', 'A'), ('@', 'TXT')}
    assert (domain['id'], domain['provider_id'], domain['registrar'], domain['expires_on']) == (
        domain_id, provider_id, 'Example Registrar', '2027-07-30')
    assert 'records replaced — 2 added, 7 removed, 0 unchanged' in response.text

    # A file with an unreadable line could drop records that still exist: the domain stays as is
    response = upload(ZONE, 'replace')
    assert 'replacement cancelled' in response.text
    assert {(r['name'], r['type']) for r in dns(unlocked)['domains'][0]['records']} == {('files', 'A'), ('@', 'TXT')}

    # A domain that is not in the list yet is created as with a normal import
    upload(zone.replace('example.com', 'example.org'), 'replace')
    assert [d['name'] for d in dns(unlocked)['domains']] == ['example.com', 'example.org']


def test_rdap_fills_form_without_saving(unlocked, monkeypatch):
    from app.routes import dns as dns_routes
    from app.services.net_tools import ToolError
    from tests.test_services.test_dns_registry import RDAP_XYZ
    calls = []
    monkeypatch.setattr(dns_routes, 'run_tool', lambda tool, data: calls.append((tool, data)) or RDAP_XYZ)

    def lookup(name, token='token'):
        return unlocked.post('/dns/rdap', json={'name': name}, headers={'X-CSRF-Token': token})

    assert lookup('example.xyz', token='wrong').status_code == 403
    response = lookup('Example.XYZ')
    assert response.status_code == 200 and calls == [('whois', {'host': 'example.xyz'})]
    assert response.json['result']['expires_on'] == '2027-07-30'
    assert response.json['result']['registrar'] == 'Example Registrar, Inc.'
    assert dns(unlocked) == {}
    assert lookup('not a domain').status_code == 400

    def fail(tool, data):
        raise ToolError('provider')
    monkeypatch.setattr(dns_routes, 'run_tool', fail)
    assert lookup('example.xyz').status_code == 502
    monkeypatch.setattr(dns_routes, 'run_tool', lambda tool, data: {})
    assert lookup('example.xyz').status_code == 404


def test_rdap_button_in_list_updates_domain(unlocked, monkeypatch):
    from app.routes import dns as dns_routes
    from tests.test_services.test_dns_registry import RDAP_XYZ
    monkeypatch.setattr(dns_routes, 'run_tool', lambda tool, data: RDAP_XYZ)
    post(unlocked, '/dns/domains/new', name='example.xyz', registrar_url='https://registrar.example/')
    domain_id = dns(unlocked)['domains'][0]['id']
    page = unlocked.get('/dns/').text
    assert f'/dns/domains/{domain_id}/rdap' in page and '0 main' in page

    assert unlocked.post(f'/dns/domains/{domain_id}/rdap').status_code == 302
    assert dns(unlocked)['domains'][0]['expires_on'] == ''

    response = post(unlocked, f'/dns/domains/{domain_id}/rdap')
    assert response.status_code == 302
    domain = dns(unlocked)['domains'][0]
    assert (domain['registrar'], domain['registered_on'], domain['expires_on']) == (
        'Example Registrar, Inc.', '2026-07-30', '2027-07-30')
    assert domain['registrar_url'] == 'https://registrar.example/'
    assert 'already matches the registry record' in unlocked.post(f'/dns/domains/{domain_id}/rdap', data={'csrf_token': 'token'},
                                               follow_redirects=True).text
