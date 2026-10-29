#!/usr/bin/env python3
"""Validate the packaged artifact and execute a relocated copy with a fresh HOME."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import tempfile
from contextlib import contextmanager

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


@contextmanager
def mounted_image(dmg, mountpoint):
    """Never write to the image; detach even if validation raises."""
    subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint',
                    str(mountpoint), str(dmg)], check=True, capture_output=True, timeout=60)
    try:
        yield mountpoint
    finally:
        subprocess.run(['hdiutil', 'detach', str(mountpoint)], check=True,
                       capture_output=True, timeout=60)


def profile_phases(executable, home, cwd, phases=('seed', 'verify', 'restore', 'verify')):
    from desktop.profile_smoke import MARKER
    (home / '.vsm-build-fixture').write_text(MARKER)
    env = dict(os.environ, HOME=str(home))
    for key in ('SECRET_KEY', 'APPDATA', 'DESKTOP_MODE'):
        env.pop(key, None)
    for phase in phases:
        result = subprocess.run([str(executable), '--build-profile-smoke', phase],
                                cwd=cwd, env=env, check=True, capture_output=True,
                                text=True, timeout=60)
        records = [line.removeprefix('VSM_PROFILE_SMOKE=') for line in result.stdout.splitlines()
                   if line.startswith('VSM_PROFILE_SMOKE=')]
        if len(records) != 1 or json.loads(records[0]) != {'phase': phase, 'status': 'passed'}:
            raise ValueError('Packaged profile check did not confirm success')


def upgrade_profile(previous_dmg, current_app, temporary, version):
    """Replace an old packaged app while keeping only its synthetic profile."""
    mountpoint = temporary / 'previous-image'
    mountpoint.mkdir()
    installed = temporary / 'upgrade-Applications' / current_app.name
    with mounted_image(previous_dmg, mountpoint) as mounted:
        old_app = mounted / current_app.name
        info = plistlib.loads((old_app / 'Contents/Info.plist').read_bytes())
        previous_version = info['CFBundleShortVersionString']
        if version_tuple(previous_version) >= version_tuple(version):
            raise ValueError('Upgrade requires a strictly older app version')
        verify(old_app)
        shutil.copytree(old_app, installed, symlinks=True)
    home = temporary / 'upgrade-home'
    home.mkdir()
    executable = installed / 'Contents/MacOS/VPNServerManager-Clean'
    profile_phases(executable, home, temporary, phases=('seed', 'verify'))
    shutil.rmtree(installed)
    shutil.copytree(current_app, installed, symlinks=True)
    verify(installed)
    profile_phases(executable, home, temporary, phases=('verify', 'restore', 'verify'))
    return {'status': 'passed', 'from_version': previous_version, 'to_version': version}


def check(root=ROOT, previous_dmg=None):
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
    upgrade = {'status': 'not_tested'}
    with tempfile.TemporaryDirectory(prefix='vsm-install-') as temporary:
        temporary = Path(temporary)
        relocated = temporary / 'Applications' / app.name
        mountpoint = temporary / 'mounted-image'
        mountpoint.mkdir()
        with mounted_image(directory / metadata['artifact'], mountpoint) as mounted:
            image_app = mounted / app.name
            image_info = plistlib.loads((image_app / 'Contents/Info.plist').read_bytes())
            validate_manifest(metadata, image_info, version)
            verify(image_app)
            shutil.copytree(image_app, relocated, symlinks=True)
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
        profile_phases(relocated / 'Contents/MacOS/VPNServerManager-Clean', home, temporary)
        if previous_dmg is not None:
            upgrade = upgrade_profile(Path(previous_dmg).resolve(), relocated, temporary, version)
    report = dict(dmg_install='passed', profile_restart='passed',
                  legacy_payload='passed', encrypted_backup_import='passed',
                  version=version, architecture=metadata['architecture'],
                  build_host_macos=platform.mac_ver()[0], relocated_runtime='passed',
                  signature='verified', dmg_sha256=digest,
                  gui_tested=False, notarized=False, upgrade=upgrade)
    (directory / 'check-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-dmg', type=Path,
                        help='Trusted older local DMG supporting --build-profile-smoke (5.0.7+)')
    args = parser.parse_args()
    check(previous_dmg=args.previous_dmg)
