import pytest
from tools.check_macos_artifact import validate_manifest


def sample():
    return ({'version': '1.2.3', 'architecture': 'arm64', 'target_macos': '13.0',
             'binary_minimum_macos': '11.0', 'notarized': False,
             'signing': 'ad-hoc-local-only', 'artifact': 'demo.dmg'},
            {'CFBundleShortVersionString': '1.2.3', 'LSMinimumSystemVersion': '13.0'})


def test_consistent_manifest_is_accepted():
    metadata, info = sample()
    validate_manifest(metadata, info, '1.2.3')


@pytest.mark.parametrize('field,value', [
    ('version', '0.0.0'), ('architecture', 'x86_64'), ('target_macos', '26.0'),
    ('binary_minimum_macos', '26.0'), ('notarized', True),
    ('artifact', '../demo.dmg'), ('artifact', '/tmp/demo.dmg'),
])
def test_misleading_manifest_is_rejected(field, value):
    metadata, info = sample()
    metadata[field] = value
    with pytest.raises(ValueError):
        validate_manifest(metadata, info, '1.2.3')


def test_image_is_detached_after_validation_failure(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from tools import check_macos_artifact as artifact
    run = Mock()
    monkeypatch.setattr(artifact.subprocess, 'run', run)
    with pytest.raises(ValueError, match='invalid bundle'):
        with artifact.mounted_image(tmp_path / 'fixture.dmg', tmp_path / 'mount'):
            raise ValueError('invalid bundle')
    assert run.call_args_list[0].args[0][:4] == ['hdiutil', 'attach', '-readonly', '-nobrowse']
    assert run.call_args_list[1].args[0] == ['hdiutil', 'detach', str(tmp_path / 'mount')]


def test_profile_smoke_refuses_regular_home(monkeypatch, tmp_path):
    from desktop import profile_smoke
    monkeypatch.setattr(profile_smoke.sys, 'frozen', True, raising=False)
    monkeypatch.setenv('HOME', str(tmp_path))
    (tmp_path / '.vsm-build-fixture').write_text(profile_smoke.MARKER)
    with pytest.raises(RuntimeError, match='disposable HOME'):
        profile_smoke.checked_home()


def test_profile_smoke_requires_frozen_executable(monkeypatch):
    from desktop import profile_smoke
    monkeypatch.setattr(profile_smoke.sys, 'frozen', False, raising=False)
    with pytest.raises(RuntimeError, match='frozen executable'):
        profile_smoke.checked_home()
