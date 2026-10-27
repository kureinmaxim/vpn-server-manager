#!/usr/bin/env python3
"""Validate the packaged artifact and execute a relocated copy with a fresh HOME."""
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import tempfile

from tools.macos_bundle import verify, version_tuple

ROOT = Path(__file__).resolve().parents[1]


def validate_manifest(metadata, info, version):
    if metadata.get('version') != version or info.get('CFBundleShortVersionString') != version:
        raise ValueError('Artifact version does not match source')
    if metadata.get('architecture') != 'arm64':
        raise ValueError('Expected an Apple Silicon artifact')
    if metadata.get('target_macos') != '13.0' or info.get('LSMinimumSystemVersion') != '13.0':
        raise ValueError('Expected macOS 13 deployment target')
    if version_tuple(metadata['binary_minimum_macos']) > (13, 0, 0):
        raise ValueError('A binary exceeds the deployment target')
    if metadata.get('notarized') is not False or metadata.get('signing') != 'ad-hoc-local-only':
        raise ValueError('This check is for local builds, not release approval')
    artifact = metadata.get('artifact', '')
    if not artifact or Path(artifact).name != artifact or not artifact.endswith('.dmg'):
        raise ValueError('Invalid artifact filename')


def check(root=ROOT):
    directory = root / 'dist/macos-local'
    version = json.loads((root / 'config/config.json.template').read_text())['app_info']['version']
    app = directory / 'VPNServerManager-Clean.app'
    manifest = directory / f'VPNServerManager-Clean-{version}-arm64-local.json'
    metadata = json.loads(manifest.read_text())
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    validate_manifest(metadata, info, version)
    with (directory / metadata['artifact']).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != metadata.get('sha256'):
        raise ValueError('DMG checksum mismatch')
    with tempfile.TemporaryDirectory(prefix='vsm-relocation-') as temporary:
        temporary = Path(temporary)
        relocated = temporary / 'Applications' / app.name
        shutil.copytree(app, relocated, symlinks=True)
        verify(relocated)
        home = temporary / 'fresh-home'
        home.mkdir()
        result = subprocess.run(
            [str(relocated / 'Contents/MacOS/VPNServerManager-Clean'), '--build-smoke-test'],
            cwd=temporary, env=dict(os.environ, HOME=str(home)),
            check=True, capture_output=True, text=True, timeout=60)
        smoke = json.loads(result.stdout.strip())
        if smoke.get('build_smoke') != 'ok' or smoke.get('frozen') is not True:
            raise ValueError('Relocated executable did not pass its self-check')
        if smoke.get('architecture') != metadata['architecture'] or smoke.get('python') != metadata['python']:
            raise ValueError('Relocated runtime does not match the manifest')
        if (home / 'Library/Application Support/VPNServerManager-Clean').exists():
            raise ValueError('Dependency smoke unexpectedly created an application profile')
    report = dict(version=version, architecture=metadata['architecture'],
                  build_host_macos=platform.mac_ver()[0], relocated_runtime='passed',
                  signature='verified', dmg_sha256=digest,
                  gui_tested=False, notarized=False)
    (directory / 'check-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    check()
