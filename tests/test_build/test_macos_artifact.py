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
