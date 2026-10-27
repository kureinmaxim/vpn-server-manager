#!/usr/bin/env python3
"""Build using an isolated, pinned CPython and hash-locked native wheels."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = '3.13.12'
TARGET = '13.0'


def main():
    if sys.platform != 'darwin':
        raise SystemExit('This build requires macOS')
    arch = platform.machine()
    if arch == 'x86_64':
        raise SystemExit('Intel build unavailable: cryptography 50 has no macOS x86_64 wheels. '
                         'No automatic downgrade to older cryptography is performed.')
    if arch != 'arm64':
        raise SystemExit(f'Unsupported build architecture: {arch}')
    uv = shutil.which('uv')
    if not uv:
        raise SystemExit('Install uv first: https://docs.astral.sh/uv/getting-started/installation/')
    env = dict(os.environ, UV_CACHE_DIR=str(ROOT / '.build-cache'),
               UV_PYTHON_INSTALL_DIR=str(ROOT / '.build-python'),
               MACOSX_DEPLOYMENT_TARGET=TARGET)
    lock = ROOT / 'requirements' / f'macos-{arch}.lock'
    if not lock.is_file():
        raise SystemExit(f'Missing dependency lock: {lock.name}')
    def run(*args):
        subprocess.run(args, cwd=ROOT, env=env, check=True)
    run(uv, 'python', 'install', PYTHON_VERSION, '--no-bin')
    distribution_arch = 'aarch64' if arch == 'arm64' else arch
    python = ROOT / '.build-python' / f'cpython-{PYTHON_VERSION}-macos-{distribution_arch}-none/bin/python3.13'
    environment = ROOT / '.venv-macos'
    run(uv, 'venv', '--python', str(python), '--allow-existing', str(environment))
    executable = environment / 'bin/python'
    run(uv, 'pip', 'sync', '--python', str(executable), '--require-hashes',
        '--only-binary', ':all:', '--no-binary', 'proxy-tools', str(lock))
    run(str(executable), '-m', 'babel.messages.frontend', 'compile', '-d', 'translations')
    run(str(executable), str(ROOT / 'build_macos.py'))


if __name__ == '__main__':
    main()
