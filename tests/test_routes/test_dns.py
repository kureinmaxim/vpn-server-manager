import re

import pytest
from cryptography.fernet import Fernet

from app.services import registry
from app.services.data_manager_service import DataManagerService


@pytest.fixture
def unlocked(app, client, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = tmp_path / 'servers.enc'
    manager.save_servers([{'id': 1, 'name': 'vps', 'ip_address': '138.124.71.73'},
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
    post(unlocked, '/dns/domains/new', name='kurein.me')
    domain_id = dns(unlocked)['domains'][0]['id']
    for name, rtype, content in [('@', 'A', '138.124.71.73'), ('vpn', 'A', '138.124.71.73'), ('www', 'CNAME', 'kurein.me')]:
        post(unlocked, f'/dns/domains/{domain_id}/records', name=name, type=rtype, content=content)
    index = unlocked.get('/').text
    assert 'collapse-dns-1' in index and 'vpn.kurein.me' in index and 'collapse-dns-2' not in index

    page = unlocked.get('/dns/move/1?to=2').text
    assert '203.0.113.9' in page and 'www.kurein.me' in page
    vpn = next(r for r in dns(unlocked)['domains'][0]['records'] if r['name'] == 'vpn')
    response = unlocked.post('/dns/move/1', data={'csrf_token': 'token', 'to': '2', 'record': [vpn['id']]})
    assert response.status_code == 302 and response.headers['Location'].endswith('/dns/move/2')
    contents = {r['name']: r['content'] for r in dns(unlocked)['domains'][0]['records']}
    assert contents == {'@': '138.124.71.73', 'vpn': '203.0.113.9', 'www': 'kurein.me'}
    assert unlocked.get('/dns/move/99').status_code == 404


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_move_page_localized(unlocked, lang):
    unlocked.get('/?lang=' + lang)
    post(unlocked, '/dns/domains/new', name='kurein.me')
    domain_id = dns(unlocked)['domains'][0]['id']
    post(unlocked, f'/dns/domains/{domain_id}/records', name='vpn', type='A', content='138.124.71.73')
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
