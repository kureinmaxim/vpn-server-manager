from unittest.mock import Mock

from app.services import registry


def test_monitoring_renders_its_stylesheet_and_section_links(client):
    """The parent layout has no head block: CSS must reach the rendered page."""
    manager = Mock()
    manager.load_servers.return_value = [{
        'id': 'demo', 'name': 'Demo VPS', 'ip_address': '192.0.2.10',
        'ssh_credentials': {'port': 22},
    }]
    registry.register('data_manager', manager)
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True)
    response = client.get('/monitoring/demo')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'css/monitoring.css?v=' in html
    for section in ('overview', 'network', 'services', 'security', 'history'):
        assert f'href="#monitoring-{section}"' in html
        assert f'id="monitoring-{section}"' in html
    # Shared interface rules come from the layout; sections switch by attribute, not by card class.
    assert 'css/ui.css?v=' in html
    assert html.count('data-mon-section=') == 5
    # In the markup, state is a dot or an icon from Bootstrap Icons, never an emoji standing in for one.
    markup = html[html.index('monitoring-page'):html.index('js/project_stats.js')]
    assert not any(mark in markup for mark in ('✅', '❌', '⚠️', '🔍', '📈'))
