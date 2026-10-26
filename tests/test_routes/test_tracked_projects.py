from app.services.project_stats import load_projects


def login(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_authenticated=True, pin_verified=True, csrf_token='token')


def test_page_lists_defaults_and_requires_login(app, client):
    assert client.get('/settings/projects').status_code in (302, 401)
    login(client)
    html = client.get('/settings/projects').get_data(as_text=True)
    assert 'value="BotCriptoM"' in html and 'value="Dockhand"' in html
    assert 'value="AdGuard Home / DNS"' in html and 'value="Chatmail relay"' in html
    assert '>botcriptom, botcriptom-dash' in html
    assert '>AdGuardHome, adguardhome, adguard-home</textarea>' in html
    assert '>doveauth, chatmail-metadata, filtermail' in html


def test_save_add_remove_and_reset(app, client, all_features):
    login(client)
    form = {'csrf_token': 'token', 'name': ['BotCriptoM', 'Blog', 'Manual RNS'],
            'units': ['botcriptom', 'ghost.service', ''], 'containers': ['', 'ghost-db', ''],
            'processes': ['', '', 'rnsd']}
    assert client.post('/settings/projects', data=form).status_code == 302
    assert [(p['name'], p['units'], p['containers'], p['processes']) for p in load_projects(app)] == [
        ('BotCriptoM', ['botcriptom'], [], []), ('Blog', ['ghost'], ['ghost-db'], []), ('Manual RNS', [], [], ['rnsd'])]
    assert '>rnsd</textarea>' in client.get('/settings/projects').get_data(as_text=True)
    assert 'Blog' in client.get('/').get_data(as_text=True)
    client.post('/settings/projects', data={'csrf_token': 'token', 'action': 'reset'})
    assert 'Dockhand' in [p['name'] for p in load_projects(app)]


def test_invalid_input_is_rejected_and_kept_in_the_form(app, client):
    login(client)
    response = client.post('/settings/projects', data={'csrf_token': 'token', 'name': ['Evil'],
                                                       'units': ['x; reboot'], 'containers': [''], 'processes': ['']})
    assert response.status_code == 400
    assert '>x; reboot</textarea>' in response.get_data(as_text=True)
    assert 'Dockhand' in [p['name'] for p in load_projects(app)]


def test_csrf_is_required(app, client):
    login(client)
    client.post('/settings/projects', data={'name': ['Blog'], 'units': ['ghost'], 'containers': [''], 'processes': ['']}, csrf=False)
    assert 'Blog' not in [p['name'] for p in load_projects(app)]
