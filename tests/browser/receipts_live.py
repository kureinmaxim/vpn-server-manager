"""Opt-in browser check against a temporary encrypted profile, never user data."""
import os
import subprocess
import threading
from pathlib import Path

from werkzeug.serving import make_server
from flask import render_template
from tests.test_routes.test_receipts import receipts  # noqa: F401


def test_keyboard_upload(app, client, receipts, tmp_path):
    source = tmp_path / 'keyboard-receipt.pdf'
    source.write_bytes(b'%PDF-1.4\nsynthetic keyboard receipt\n')
    token = 'synthetic-browser-csrf'
    cookie = app.session_interface.get_signing_serializer(app).dumps(dict(
        authenticated=True, pin_verified=True, pin_authenticated=True, csrf_token=token))
    @app.get('/__keyboard_ssh/<screen>')
    def ssh_fixture(screen):
        servers = receipts[0].load_servers(app.config)
        template = 'index.html' if screen == 'stats' else 'monitoring.html'
        html = render_template(template, servers=servers, server=servers[0], service_urls={}, dns_links={})
        # Transport is synthetic: keyboard tests must never execute SSH operations.
        stub = "<script>window.fetch=async()=>({ok:false,status:503,json:async()=>({error:'Synthetic SSH unavailable'})});</script>"
        return html.replace('<head>', '<head>' + stub)

    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        subprocess.run(['node', 'tests/browser/receipts_keyboard.mjs'], check=True, timeout=90,
                       env={**os.environ, 'KEYBOARD_URL': f'http://127.0.0.1:{server.server_port}',
                            'KEYBOARD_COOKIE_NAME': app.config['SESSION_COOKIE_NAME'], 'KEYBOARD_COOKIE': cookie, 'KEYBOARD_FILE': str(source)})
        stored = receipts[0].load_servers(app.config)[0]['payment_info']['receipts']
        assert len(stored) == 1
        assert stored[0]['description'] == 'Keyboard receipt'
        uploaded = Path(app.config['UPLOAD_FOLDER']) / 'receipts' / stored[0]['filename']
        assert uploaded.read_bytes() == source.read_bytes()
    finally:
        server.shutdown()
        thread.join(timeout=5)
