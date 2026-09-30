import json

import pytest
from app.services import protocol_inspection as inspection


def inventory(runtime='docker'):
    return {'hostname': 'fixture', 'components': [
        {'key': 'bot', 'instances': [{'runtime': runtime, 'id': 'a'*64 if runtime == 'docker' else 'telegramonly.service', 'state': 'exited'}]},
        {'key': 'xui', 'instances': []}]}


def test_summary_never_returns_secret_fields():
    data = {'server': 'example.com', 'port': 443, 'password': 'secret', 'secret': 'secret', 'private_key': 'secret',
            'clients': [{'name': 'alice', 'uuid': 'secret', 'password': 'secret'}], 'future_field': 'secret',
            'port_bindings': [{'port': 1234, 'protocol': 'TCP', 'password': 'secret'}]}
    summary = inspection.summarize(data)
    assert summary['client_count'] == 1
    assert summary['fields'] == {'server': 'example.com', 'port': 443}
    assert 'secret' not in json.dumps(summary)
    assert 'alice' not in json.dumps(summary)


def test_read_bounds_and_revision(tmp_path):
    path = tmp_path / 'anytls_config.json'
    path.write_text('{"server":"example.com"}')
    first = inspection.read_metadata(path)[1]
    path.write_text('{"server":"example.org"}')
    assert inspection.read_metadata(path)[1] != first
    path.write_text('x' * (1024 * 1024 + 1))
    with pytest.raises(ValueError):
        inspection.read_metadata(path)


@pytest.mark.parametrize('content', ['[]', 'invalid JSON', 'null'])
def test_invalid_metadata(tmp_path, content):
    path = tmp_path / 'anytls_config.json'
    path.write_text(content)
    with pytest.raises(ValueError):
        inspection.read_metadata(path)


def test_stopped_docker_bot_uses_inspect_not_exec(monkeypatch):
    monkeypatch.setattr(inspection, 'DEFAULT_ROOTS', ())
    calls = []
    def run(args):
        calls.append(args)
        return 0, json.dumps([{'Type': 'bind', 'Source': '/data/anytls_config.json', 'Destination': '/app/anytls_config.json'}])
    result = inspection.sources(inventory(), run)
    assert result['anytls'] == [('/data/anytls_config.json', 'telegramonly-docker')]
    assert calls == [['docker', 'inspect', '--format', '{{json .Mounts}}', 'a'*64]]


def test_systemd_custom_working_directory(monkeypatch):
    monkeypatch.setattr(inspection, 'DEFAULT_ROOTS', ())
    result = inspection.sources(inventory('systemd'), lambda args: (0, '/srv/my-bot\n'))
    assert result['tuic'] == [('/srv/my-bot/tuic_config.json', 'telegramonly-systemd')]


def test_multiple_sources_not_silently_selected(monkeypatch):
    candidates = {key: [] for key in inspection.PROTOCOL_FILES}
    candidates['anytls'] = [('/opt/one/anytls_config.json', 'candidate'), ('/opt/two/anytls_config.json', 'telegramonly-docker')]
    monkeypatch.setattr(inspection, 'sources', lambda *a: candidates)
    monkeypatch.setattr(inspection, 'read_metadata', lambda path: ({'port': 443}, 'revision'))
    data = inspection.inspect_protocols(inventory(), lambda args: (0, ''))
    anytls = next(p for p in data['protocols'] if p['key'] == 'anytls')
    assert anytls['ownership'] == 'ambiguous'
    assert len(anytls['sources']) == 2


def test_xui_blocks_ownership_assumption(monkeypatch):
    monkeypatch.setattr(inspection, 'sources', lambda *a: {key: [] for key in inspection.PROTOCOL_FILES})
    data = inventory()
    data['components'][1]['instances'] = [{'runtime': 'systemd', 'id': 'x-ui.service'}]
    result = inspection.inspect_protocols(data, lambda args: (0, ''))
    assert next(p for p in result['protocols'] if p['key'] == 'vless')['ownership'] == 'xui_detected'


def test_errors_are_redacted(monkeypatch):
    monkeypatch.setattr(inspection, 'sources', lambda *a: {key: [('/data/' + name, 'candidate')] for key, name in inspection.PROTOCOL_FILES.items()})
    def invalid(path):
        raise ValueError('private-password')
    monkeypatch.setattr(inspection, 'read_metadata', invalid)
    result = inspection.inspect_protocols(inventory(), lambda args: (0, ''))
    assert 'private-password' not in json.dumps(result)
    assert all(p['sources'][0]['error'] == 'unreadable' for p in result['protocols'])
