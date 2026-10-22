import json
import subprocess
from types import SimpleNamespace

from app.services import mesh_context as mesh


def test_local_mesh_filters_private_fields(monkeypatch):
    monkeypatch.setattr(mesh.shutil, 'which', lambda _: '/test/tailscale')
    responses = iter([
        {'BackendState':'Running', 'Self':{'ID':'self','HostName':'pc'},
         'CurrentTailnet':{'Name':'test-net'}, 'Peer':{'key':{'ID':'peer','HostName':'server',
         'TailscaleIPs':['100.64.0.9'],'ExitNodeOption':True,'ExitNode':True,'Online':False,
         'Addrs':['192.0.2.80:41641'],'Relay':'fra',
         'PublicKey':'private-marker','UserID':999}}},
        {'ControlURL':'https://control.example.com/path?token=secret-marker', 'PrivateNodeKey':'secret-marker'}])
    monkeypatch.setattr(mesh.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0,stdout=json.dumps(next(responses))))
    monkeypatch.setattr(mesh.socket, 'getaddrinfo', lambda *a: [(None,None,None,None,('192.0.2.1',0))])
    result = mesh.local_mesh()
    assert result['state'] == 'ready' and result['coordinator'] == 'control.example.com'
    assert result['coordinator_ips'] == ['192.0.2.1']
    assert result['nodes'][1]['exit_selected'] and result['nodes'][1]['exit_available']
    assert result['nodes'][1]['endpoints'] == ['192.0.2.80'] and result['nodes'][1]['relay'] == 'fra'
    assert 'secret-marker' not in json.dumps(result) and 'private-marker' not in json.dumps(result)


def test_card_marks_match_ip_hostname_exit_coordinator_and_derp():
    node = mesh.public_node({
        'ID': 'peer', 'HostName': 'hiplet', 'DNSName': 'hiplet.example.ts.net.',
        'TailscaleIPs': ['100.64.1.8'], 'Addrs': ['192.0.2.80:41641'],
        'ExitNodeOption': True, 'ExitNode': True, 'Online': True, 'Relay': 'fra',
    })
    mesh_data = {'state': 'ready', 'nodes': [node],
                 'coordinator': 'headscale.example.net', 'coordinator_ips': ['192.0.2.80']}
    by_ip = mesh.card_marks('100.64.1.8', 'other', mesh_data)
    by_name = mesh.card_marks('203.0.113.9', 'HIP-Hosting hiplet', mesh_data)
    by_endpoint = mesh.card_marks('192.0.2.80', 'HIP-Hosting hiplet', mesh_data)
    for marks in (by_ip, by_name, by_endpoint):
        assert marks['mesh'] and marks['exit_selected'] and marks['relay'] == 'fra'
    assert by_endpoint['coordinator'] is True
    assert mesh.card_marks('203.0.113.9', 'unrelated', mesh_data) == {}
    assert mesh.card_marks('192.0.2.80', 'x', {'state': 'unavailable', 'nodes': [node]}) == {}


def test_daemon_failure_does_not_claim_other_mesh(monkeypatch):
    monkeypatch.setattr(mesh.shutil, 'which', lambda _: '/test/tailscale')
    def fail(*a, **k): raise subprocess.TimeoutExpired('tailscale', 4)
    monkeypatch.setattr(mesh.subprocess, 'run', fail)
    assert mesh.local_mesh() == {'state':'unavailable','nodes':[]}


def test_remote_snapshot_only_returns_self():
    data = {'BackendState':'Running','Self':{'ID':'node','TailscaleIPs':['100.64.0.9']},'Peer':{'secret':'hidden'}}
    result = mesh.remote_mesh('metrics\nVPN_MESH_BEGIN\n'+json.dumps(data)+'\nVPN_MESH_END\n')
    assert result['self']['id'] == 'node' and 'hidden' not in json.dumps(result)
    assert mesh.remote_mesh('metrics') == {'state':'unavailable'}


def test_macos_app_bundle_finds_cli_outside_path(monkeypatch, tmp_path):
    cli = tmp_path / 'Tailscale'
    cli.write_text('#!/bin/sh\n'); cli.chmod(0o755)
    monkeypatch.setattr(mesh.shutil, 'which', lambda _: None)
    monkeypatch.setattr(mesh.os, 'name', 'posix')
    monkeypatch.setattr(mesh.sys, 'platform', 'darwin')
    monkeypatch.setattr(mesh, '_fallback_paths', lambda: [tmp_path / 'missing', cli])
    assert mesh.tailscale_executable() == str(cli)
