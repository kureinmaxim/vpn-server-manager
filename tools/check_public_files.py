"""Fail closed on private files in Git or installer source directories.

Reports paths only, never file contents. No dependencies beyond Python.
"""
from pathlib import Path
import fnmatch
import subprocess
import sys

PRIVATE_NAMES = ('.env', '.env.*', '*.enc', '*.key', '*.pem', '*.p12', '*.pfx',
                 'client_secret*.json', 'credentials*.json')
PACKAGE_DIRS = ('app', 'desktop', 'static', 'templates', 'translations', 'tests', 'docs')


def is_private(path):
    path = Path(path)
    if path.name in ('.env.example', 'env.example'):
        return False
    return (any(fnmatch.fnmatch(path.name.lower(), pattern) for pattern in PRIVATE_NAMES)
            or path.as_posix().lower() in ('config.json', 'data/hints.json')
            or (path.parts and path.parts[0] == 'data' and path.suffix == '.json'))


def check(root):
    findings = []
    tracked = subprocess.check_output(['git', '-c', 'safe.directory=' + root.as_posix(),
                                      'ls-files', '-z'], cwd=root, stderr=subprocess.DEVNULL)
    for name in tracked.decode('utf-8').split('\0'):
        if name and is_private(name):
            findings.append('Tracked private file: ' + name)
    for directory in PACKAGE_DIRS:
        for path in (root / directory).rglob('*'):
            if path.is_file() and is_private(path.relative_to(root)):
                findings.append('Private file in package source: ' + path.relative_to(root).as_posix())
    return findings


if __name__ == '__main__':
    try:
        findings = check(Path(__file__).resolve().parents[1])
    except (OSError, subprocess.SubprocessError):
        print('Privacy check could not inspect the Git index; build stopped.')
        sys.exit(1)
    for finding in findings:
        print(finding)
    print('Privacy file check: ' + ('FAILED' if findings else 'OK (paths; not a full secret scan)'))
    sys.exit(bool(findings))
