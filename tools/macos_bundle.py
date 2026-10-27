"""Finalize local macOS builds; no profile access or publication side effects."""
import hashlib
import json
import plistlib
import re
import subprocess
from pathlib import Path

MACH_MAGICS = {bytes.fromhex(value) for value in (
    'feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca',
    'cafebabf', 'bfbafeca')}


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def minimum_os(output):
    """Only deployment targets, never the build SDK version."""
    versions = []
    for block in re.split(r'^Load command \d+\s*$', output, flags=re.M):
        if re.search(r'^\s*cmd LC_BUILD_VERSION\s*$', block, re.M):
            field = 'minos'
            # LC_BUILD_VERSION for iOS/tvOS is not a macOS dependency.
            if not re.search(r'^\s*platform (?:1|macos|MACOS)\s*$', block, re.M):
                raise ValueError('Non-macOS build platform')
        elif re.search(r'^\s*cmd LC_VERSION_MIN_MACOSX\s*$', block, re.M):
            field = 'version'
        else:
            continue
        match = re.search(r'^\s*' + field + r'\s+(\d+\.\d+(?:\.\d+)?)\s*$', block, re.M)
        if not match:
            raise ValueError('Malformed deployment target')
        versions.append(match.group(1))
    if not versions:
        raise ValueError('Mach-O deployment target is missing')
    return max(versions, key=version_tuple)


def version_tuple(value):
    return tuple(map(int, value.split('.'))) + (0,) * (3 - len(value.split('.')))


def inspect_binaries(app):
    binaries = []
    for path in app.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) not in MACH_MAGICS:
                continue
        arches = set(run('lipo', '-archs', str(path)).strip().split())
        minimum = minimum_os(run('otool', '-l', str(path)))
        binaries.append((path, arches, minimum))
    if not binaries:
        raise ValueError('No Mach-O binaries found')
    return binaries


def require_compatible(binaries, target, root):
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', target):
        raise ValueError('Invalid macOS target')
    incompatible = [(path, minimum) for path, _, minimum in binaries
                    if version_tuple(minimum) > version_tuple(target)]
    if incompatible:
        details = ', '.join(f'{path.relative_to(root)} requires {minimum}'
                            for path, minimum in incompatible[:8])
        raise ValueError(f'Build exceeds macOS {target}: {details}. '
                         'Use python3 tools/build_macos_compatible.py; changing plist is not a fix.')


def verify(app):
    run('codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app))


def finalize(app, template, version, target=None):
    app = Path(app)
    plist_path = app / 'Contents/Info.plist'
    with plist_path.open('rb') as stream:
        info = plistlib.load(stream)
    executable = app / 'Contents/MacOS' / info['CFBundleExecutable']
    binaries = inspect_binaries(app)
    arches = next(arches for path, arches, _ in binaries if path == executable)
    if arches not in ({'arm64'}, {'x86_64'}, {'arm64', 'x86_64'}):
        raise ValueError('Unsupported application architecture')
    for path, available, _ in binaries:
        if not arches <= available:
            raise ValueError(f'Architecture mismatch: {path.relative_to(app)}')
    if target is not None:
        require_compatible(binaries, target, app)
    minimum = max((minimum for _, _, minimum in binaries), key=version_tuple)
    if 'arm64' in arches and version_tuple(minimum) < (11, 0, 0):
        minimum = '11.0'
    overlay = plistlib.loads(Path(template).read_text().replace('{{VERSION}}', version).encode())
    # PyInstaller owns executable/layout/icon names; preserve these exact values.
    for key in ('CFBundleExecutable', 'CFBundleIconFile'):
        overlay.pop(key, None)
    info.update(overlay)
    info['LSMinimumSystemVersion'] = max((minimum, target or minimum), key=version_tuple)
    with plist_path.open('wb') as stream:
        plistlib.dump(info, stream)
    # PyInstaller has already signed nested binaries. Only the outer seal changed.
    run('codesign', '--force', '--sign', '-', str(app))
    verify(app)
    return {'version': version, 'architecture': 'universal2' if len(arches) == 2 else next(iter(arches)),
            'minimum_macos': info['LSMinimumSystemVersion'], 'binary_minimum_macos': minimum, 'signing': 'ad-hoc-local-only',
            'notarized': False, 'binary_count': len(binaries), 'target_macos': target}


def write_manifest(dmg, metadata):
    digest = hashlib.sha256()
    with Path(dmg).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    result = dict(metadata, artifact=Path(dmg).name, sha256=digest.hexdigest())
    path = Path(dmg).with_suffix('.json')
    path.write_text(json.dumps(result, indent=2) + '\n')
    return path
