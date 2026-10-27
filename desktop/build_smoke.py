"""Packaged-runtime check without profiles, remote connections or GUI windows."""
import json
import platform
import sys


def run():
    # Explicit imports also let PyInstaller discover these native dependencies.
    import ssl
    import ctypes
    import flask
    import flask_babel
    import paramiko
    import PIL.Image
    import webview
    import AppKit
    import WebKit
    import Security
    from cryptography.fernet import Fernet
    cipher = Fernet(Fernet.generate_key())
    if cipher.decrypt(cipher.encrypt(b'build-check')) != b'build-check':
        raise RuntimeError('Cryptography self-check failed')
    print(json.dumps({'build_smoke': 'ok', 'python': platform.python_version(),
                      'architecture': platform.machine(), 'frozen': bool(getattr(sys, 'frozen', False))}))
