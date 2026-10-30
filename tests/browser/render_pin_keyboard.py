from pathlib import Path
def test_preview(client):
    html=client.get('/locked').text
    html=html.replace('"/static/', '"file://'+str(Path.cwd()/'static')+'/')
    html=html.replace('<head>', '<head><script>window.fetch=async()=>({ok:true,json:async()=>({allowed:false,authenticated:true,blocked:false})});</script>')
    Path('/tmp/vsm-modal.html').write_text(html)
