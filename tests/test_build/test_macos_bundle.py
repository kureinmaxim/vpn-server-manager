import plistlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from tools import macos_bundle as bundle


def fixture_app(tmp_path):
    app = tmp_path / 'Demo.app'
    executable = app / 'Contents/MacOS/Demo'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'fixture')
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': 'Demo', 'CFBundleIdentifier': 'com.example.demo',
        'CFBundlePackageType': 'APPL', 'CFBundleIconFile': 'generated.icns'}))
    return app, executable


def test_deployment_target_ignores_sdk():
    assert bundle.minimum_os('Load command 1\n cmd LC_BUILD_VERSION\n platform 1\n minos 11.0\n sdk 15.0\nLoad command 2\n cmd LC_VERSION_MIN_MACOSX\n version 12.3\nLoad command 3\n cmd LC_SOURCE_VERSION\n version 1267.0\n') == '12.3'
    with pytest.raises(ValueError):
        bundle.minimum_os('sdk 15.0')


def test_final_plist_is_signed_then_verified(tmp_path, monkeypatch):
    app, executable = fixture_app(tmp_path)
    monkeypatch.setattr(bundle, 'inspect_binaries', lambda _: [(executable, {'arm64'}, '12.0')])
    calls = []
    def run(*args):
        info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
        assert info['CFBundleVersion'] == '1.2.3'
        assert info['LSMinimumSystemVersion'] == '12.0'
        assert info['CFBundleExecutable'] == 'Demo'
        assert info['CFBundleIconFile'] == 'generated.icns'
        calls.append(args)
    monkeypatch.setattr(bundle, 'run', run)
    result = bundle.finalize(app, 'Info.plist.template', '1.2.3')
    assert result['architecture'] == 'arm64'
    assert result['notarized'] is False
    assert calls[0][1:4] == ('--force', '--sign', '-')
    assert calls[1][1:4] == ('--verify', '--deep', '--strict')


def test_missing_architecture_fails_before_signing(tmp_path, monkeypatch):
    app, executable = fixture_app(tmp_path)
    monkeypatch.setattr(bundle, 'inspect_binaries', lambda _: [
        (executable, {'arm64'}, '11.0'), (app / 'dependency', {'x86_64'}, '12.0')])
    run = Mock()
    monkeypatch.setattr(bundle, 'run', run)
    with pytest.raises(ValueError, match='Architecture mismatch'):
        bundle.finalize(app, 'Info.plist.template', '1.2.3')
    run.assert_not_called()


def test_signature_failure_is_fatal(tmp_path, monkeypatch):
    app, executable = fixture_app(tmp_path)
    monkeypatch.setattr(bundle, 'inspect_binaries', lambda _: [(executable, {'x86_64'}, '12.0')])
    monkeypatch.setattr(bundle, 'run', Mock(side_effect=subprocess.CalledProcessError(1, 'codesign')))
    with pytest.raises(subprocess.CalledProcessError):
        bundle.finalize(app, 'Info.plist.template', '1.2.3')


def test_manifest_contains_digest_without_local_paths(tmp_path):
    import hashlib
    dmg = tmp_path / 'demo.dmg'
    dmg.write_bytes(b'archive')
    manifest = bundle.write_manifest(dmg, {'notarized': False}).read_text()
    assert hashlib.sha256(b'archive').hexdigest() in manifest
    assert str(tmp_path) not in manifest


def test_builder_uses_template_and_does_not_touch_profile():
    import build_macos
    assert build_macos.get_build_metadata_sources() == [build_macos.PROJECT_ROOT / 'config/config.json.template']
    source = Path('build_macos.py').read_text()
    assert 'shutil.copy2(project_config, user_config)' not in source
    assert 'symlinks=True' in source


@pytest.mark.skipif(sys.platform != 'darwin', reason='Apple signing tools required')
def test_real_codesign_detects_post_signing_plist_change(tmp_path):
    app, executable = fixture_app(tmp_path)
    source = tmp_path / 'main.c'
    source.write_text('int main(void) { return 0; }\n')
    subprocess.run(['clang', str(source), '-o', str(executable)], check=True, capture_output=True)
    bundle.finalize(app, 'Info.plist.template', '1.2.3')
    bundle.verify(app)
    info_path = app / 'Contents/Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    info['CFBundleVersion'] = 'modified'
    info_path.write_bytes(plistlib.dumps(info))
    with pytest.raises(subprocess.CalledProcessError):
        bundle.verify(app)


def test_newer_dependency_rejected_before_plist_changes(tmp_path, monkeypatch):
    app, executable = fixture_app(tmp_path)
    before = (app / 'Contents/Info.plist').read_bytes()
    monkeypatch.setattr(bundle, 'inspect_binaries', lambda _: [
        (executable, {'arm64'}, '11.0'), (app / 'libpython.dylib', {'arm64'}, '26.0')])
    run = Mock()
    monkeypatch.setattr(bundle, 'run', run)
    with pytest.raises(ValueError, match='libpython.dylib requires 26.0'):
        bundle.finalize(app, 'Info.plist.template', '1.2.3', target='13.0')
    assert (app / 'Contents/Info.plist').read_bytes() == before
    run.assert_not_called()


def test_supported_target_is_not_lowered_to_binary_minimum(tmp_path, monkeypatch):
    app, executable = fixture_app(tmp_path)
    monkeypatch.setattr(bundle, 'inspect_binaries', lambda _: [(executable, {'arm64'}, '11.0')])
    monkeypatch.setattr(bundle, 'run', Mock())
    result = bundle.finalize(app, 'Info.plist.template', '1.2.3', target='13.0')
    assert result['minimum_macos'] == '13.0'
    assert result['binary_minimum_macos'] == '11.0'
    assert plistlib.loads((app / 'Contents/Info.plist').read_bytes())['LSMinimumSystemVersion'] == '13.0'


def test_intel_build_explains_missing_dependency_before_download(monkeypatch):
    from tools import build_macos_compatible as compatible
    monkeypatch.setattr(compatible.sys, 'platform', 'darwin')
    monkeypatch.setattr(compatible.platform, 'machine', lambda: 'x86_64')
    run = Mock()
    monkeypatch.setattr(compatible.subprocess, 'run', run)
    with pytest.raises(SystemExit, match='cryptography 50'):
        compatible.main()
    run.assert_not_called()
