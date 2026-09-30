import re

import pytest
from cryptography.fernet import Fernet

from app.services import registry
from app.services.data_manager_service import DataManagerService


@pytest.fixture
def unlocked(app, client, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = tmp_path / 'servers.enc'
    manager.save_servers([{'id': 1, 'name': 'vps'}], str(path))
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
