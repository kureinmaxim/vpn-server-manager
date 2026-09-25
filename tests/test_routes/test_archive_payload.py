import io
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.services.archive_payload import ARCHIVE_SOURCE


@pytest.fixture
def payload(monkeypatch):
    monkeypatch.setitem(sys.modules, 'fcntl', SimpleNamespace(flock=Mock(), LOCK_EX=1, LOCK_NB=2))
    scope = {'__name__': 'archive_payload_test'}
    exec(compile(ARCHIVE_SOURCE, '<archive payload>', 'exec'), scope)
    scope['open'] = lambda *args: io.StringIO()
    monkeypatch.setattr(scope['os'], 'geteuid', lambda: 0, raising=False)
    monkeypatch.setattr(scope['socket'], 'gethostname', lambda: 'vps')
    scope['inventory'] = lambda: [{'name': '20260925-120000-aaaaaaaaaaaa', 'hash': 'abc'}]
    remover = Mock()
    remover.avoids_symlink_attacks = True
    monkeypatch.setattr(scope['shutil'], 'rmtree', remover)
    return scope, remover


@pytest.mark.parametrize('args', [
    ['20260925-120000-aaaaaaaaaaaa', 'abc', 'wrong-host'],
    ['20260925-120000-aaaaaaaaaaaa', 'changed-hash', 'vps'],
    ['../../etc', 'abc', 'vps'],
])
def test_payload_refuses_changed_or_unconfirmed_target(payload, monkeypatch, args):
    scope, remover = payload
    monkeypatch.setattr(sys, 'argv', ['script'] + args)
    with pytest.raises(ValueError):
        scope['main']()
    remover.assert_not_called()


def test_payload_deletes_only_fixed_root_child(payload, monkeypatch):
    scope, remover = payload
    monkeypatch.setattr(sys, 'argv', ['script', '20260925-120000-aaaaaaaaaaaa', 'abc', 'vps'])
    scope['main']()
    remover.assert_called_once_with(Path('/var/backups/telegramonly-reset/20260925-120000-aaaaaaaaaaaa'))


def test_payload_refuses_unsafe_remover(payload, monkeypatch):
    scope, remover = payload
    remover.avoids_symlink_attacks = False
    monkeypatch.setattr(sys, 'argv', ['script', '20260925-120000-aaaaaaaaaaaa', 'abc', 'vps'])
    with pytest.raises(ValueError):
        scope['main']()
    remover.assert_not_called()
