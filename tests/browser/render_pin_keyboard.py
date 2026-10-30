from pathlib import Path
def test_preview(client):
    html=client.get('/locked').text
    html=html.replace('"/static/', '"file://'+str(Path.cwd()/'static')+'/')
    html=html.replace('<head>', '<head><script>window.fetch=async()=>({ok:true,json:async()=>({allowed:false,authenticated:true,blocked:false})});</script>')
    Path('/tmp/vsm-modal.html').write_text(html)


def test_render_settings_and_add(client, app):
    app.config['active_data_file'] = '/tmp/synthetic-vault.enc'
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, pin_authenticated=True)
    for name, url in [('settings', '/settings'), ('add', '/add_server')]:
        response = client.get(url)
        assert response.status_code == 200
        html = response.text.replace('"/static/', '"file://' + str(Path.cwd() / 'static') + '/')
        html = html.replace('<head>', '<head><script>window.fetch=async()=>({ok:true,json:async()=>({success:true})});</script>')
        Path('/tmp/vsm-' + name + '.html').write_text(html)
