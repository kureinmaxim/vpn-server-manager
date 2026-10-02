"""Local Linux filesystem integration; simulated service, no networking."""
import copy, hashlib, importlib, json, os, sys, tempfile, types
from pathlib import Path
root = Path(__file__).resolve().parent.parent
for name, path in [('app', root/'app'), ('app.services', root/'app/services')]:
    module = types.ModuleType(name); module.__path__ = [str(path)]; sys.modules[name] = module
edits = importlib.import_module('app.services.protocol_mutations')
edits.time.sleep = lambda _: None
passed = 0
for scenario in ('success', 'restart_failure', 'write_failure', 'late_failure', 'recovery_failure', 'symlink', 'writable'):
    with tempfile.TemporaryDirectory(prefix='vpn-manager-test-', dir='/root') as directory:
        base = Path(directory)
        source, live = base/'manager.json', base/'live.json'
        manager = {'port':443, 'clients':[{'name':'fixture','password':'test-only-password'}]}
        runtime = {'inbounds':[{'type':'anytls','listen_port':443,'users':copy.deepcopy(manager['clients']),
            'tls':{'enabled':True,'certificate_path':'/etc/anytls/server.crt','key_path':'/etc/anytls/server.key'}}]}
        source.write_text(json.dumps(manager)); live.write_text(json.dumps(runtime))
        originals = source.read_bytes(), live.read_bytes()
        edits.ANYTLS_CONFIG = str(live); edits.MUTATION_BACKUPS = str(base/'backups')
        edits.sources = lambda *a: {'anytls': [(str(source),'candidate')]}
        inventory = {'hostname':'fixture-vps', 'components':[{'key':'anytls','instances':[
            {'runtime':'systemd','state':'active','id':'anytls.service'}]}]}
        restarts = 0; checks = 0
        def run(argv):
            global restarts, checks
            if argv[:2] == ['systemctl','show']:
                return 0, '{ path=/usr/bin/sing-box ; argv[]=/usr/bin/sing-box run -c '+str(live)+' ; ignore_errors=no ; }'
            if 'check' in argv: return 0, ''
            if argv[:2] == ['systemctl','restart']:
                restarts += 1
                return (1 if scenario == 'recovery_failure' or (scenario == 'restart_failure' and restarts == 1) else 0), ''
            if argv[:2] == ['systemctl','is-active']:
                checks += 1
                return (3, 'failed') if scenario == 'late_failure' and checks == 2 else (0,'active')
            raise AssertionError('Unexpected command')
        body = {'component':'anytls','action':'configure','source_id':hashlib.sha256(str(source).encode()).hexdigest(),
                'revision':hashlib.sha256(source.read_bytes()).hexdigest(),'change':{'kind':'add_client','name':'second'}}
        plan = edits.prepare_mutation(body, inventory, run)[0]
        body.update(plan_hash=plan['plan_hash'],confirmation=plan['hostname'])
        if scenario in ('symlink','writable'):
            if scenario == 'symlink':
                linked = base/'linked'; linked.symlink_to(source)
                target = linked
            else: target=source; source.chmod(0o666)
            try: edits.snapshot(target)
            except (ValueError,OSError): passed += 1; continue
            raise AssertionError('Unsafe file was accepted')
        real_replace = edits.durable_replace
        failed = False
        def replace(path, raw, info):
            global failed
            real_replace(path, raw, info)
            if scenario == 'write_failure' and str(path) == str(live) and not failed:
                failed = True; raise OSError('simulated error after rename')
        edits.durable_replace = replace
        try: result = edits.apply_mutation(body, inventory, run, lambda: inventory)
        finally: edits.durable_replace = real_replace
        if scenario == 'success':
            assert result['success']
            assert len(json.loads(source.read_bytes())['clients']) == 2
            assert edits.snapshot(source)[1].st_uid == 0
        else:
            assert result['error'] == ('recovery_required' if scenario=='recovery_failure' else 'rolled_back')
            assert (source.read_bytes(),live.read_bytes()) == originals
        backup=Path(result['backup'])
        assert backup.stat().st_mode & 0o777 == 0o700
        assert (backup/'0.json').stat().st_mode & 0o777 == 0o600
        assert (backup/'0.json').read_bytes() == originals[0]
        assert json.loads((backup/'manifest.json').read_text())['files'][0]['path'] == str(source)
        assert (base/'backups/anytls-pending.json').exists() == (scenario == 'recovery_failure')
        passed += 1
print(f'Linux filesystem integration: {passed} scenarios passed; no real services or networks used.')
