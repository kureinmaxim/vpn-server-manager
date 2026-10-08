import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import derp_context as derp
from app.services import derp_probe as probe
from app.services.mesh_context import public_node, read_tailscale
from app.services.remote_derp import parse_remote_derp
from app.services.ssh_service import SSHService


STATUS = {'BackendState': 'Running', 'Self': {'ID': 'pc', 'Relay': 'ams'},
          'Peer': {'key': {'ID': 'exit', 'HostName': 'exit-demo', 'ExitNode': True}}}
MAP = {'Regions': {str(i): {'RegionID': i, 'RegionCode': 'r' + str(i), 'RegionName': 'Region ' + str(i),
                          'Nodes': [{'HostName': 'relay.example.com'}]} for i in range(1, 7)}}
MAP['Regions']['999'] = {'RegionID': 999, 'RegionCode': 'custom', 'RegionName': 'Private relay',
                         'Nodes': [{'HostName': 'control.example.com'}]}
CONFIG = '''server_url: https://control.example.com
private_key_path: /private/secret-marker
derp:
  server:
    enabled: true
    region_id: 999
    region_code: custom
    region_name: "Private relay"
    stun_listen_addr: "0.0.0.0:3478"
    verify_clients: true
    ipv4: 192.0.2.10
    private_key_path: /private/secret-marker
  urls:
    - https://controlplane.tailscale.com/derpmap/default
'''


def test_nearest_five_plus_own_and_nanosecond_conversion():
    report = {'UDP': False, 'PreferredDERP': 1, 'RegionLatency': {str(i): i * 1000000 for i in range(1, 7)}}
    report['RegionLatency']['999'] = 59000000
    result = derp.summarize_derp(STATUS, report, MAP)
    assert [r['id'] for r in result['regions']] == [1, 2, 3, 4, 5, 999]
    assert result['regions'][-1]['latency_ms'] == 59
    assert result['regions'][-1]['own'] is True
    assert result['udp'] is False and result['home_relay'] == 'ams'
    assert result['preferred'] == 'r1' and result['exit_name'] == 'exit-demo'
    assert result['exit_selected'] is True


def test_own_by_hostname_and_unknown_latency_are_retained():
    result = derp.summarize_derp({}, {'RegionLatency': {'1': float('nan'), '2': -1}}, MAP, 'relay.example.com')
    assert len(result['regions']) == 7
    assert all(r['own'] and r['latency_ms'] is None for r in result['regions'])
    assert result['udp'] is None and result['exit_selected'] is False


def test_exit_status_warns_even_without_peer_details():
    result = derp.summarize_derp({'ExitNodeStatus': {'ID': 'hidden'}}, {}, MAP)
    assert result['exit_selected'] is True


def test_paths_allowlisted_and_missing_fields_unknown():
    node = public_node({'CurAddr': '192.0.2.10:41641', 'Relay': 'ams', 'PrivateKey': 'secret-marker'})
    assert node['cur_addr'] == '192.0.2.10:41641' and node['relay'] == 'ams'
    assert 'secret-marker' not in json.dumps(node)
    assert public_node({})['cur_addr'] == '' and public_node({})['relay'] == ''


def test_windows_json_prefix_and_output_limit(monkeypatch):
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout='diagnostic\n{"UDP":false}\n'))
    monkeypatch.setattr('app.services.mesh_context.subprocess.run', run)
    assert read_tailscale('tailscale', ['netcheck', '--format=json'], 12) == {'UDP': False}
    assert run.call_args.kwargs['timeout'] == 12
    run.return_value.stdout = ' ' * (4 * 1024 * 1024 + 1)
    with pytest.raises(ValueError): read_tailscale('tailscale', [])


def test_local_cache_does_not_repeat_netcheck_or_expose_prefs(monkeypatch):
    monkeypatch.setattr(derp, '_cache', None)
    monkeypatch.setattr(derp, '_expires', 0)
    monkeypatch.setattr(derp, 'tailscale_executable', lambda: 'tailscale')
    read = Mock(side_effect=[STATUS, {'ControlURL': 'https://control.example.com', 'key': 'secret-marker'},
                             MAP, {'UDP': True, 'PreferredDERP': 1, 'RegionLatency': {'999': 50000000}}])
    monkeypatch.setattr(derp, 'read_tailscale', read)
    first = derp.local_derp()
    assert first == derp.local_derp() and read.call_count == 4
    assert 'secret-marker' not in json.dumps(first)
    assert 0 < read.call_args.kwargs['timeout'] <= 12


def test_netcheck_timeout_keeps_own_regions_unknown(monkeypatch):
    monkeypatch.setattr(derp, '_cache', None)
    monkeypatch.setattr(derp, 'tailscale_executable', lambda: 'tailscale')
    monkeypatch.setattr(derp, 'read_tailscale', Mock(side_effect=[STATUS, {}, MAP, subprocess.TimeoutExpired('netcheck', 12)]))
    result = derp.local_derp()
    assert result['state'] == 'ready' and result['udp'] is None
    assert result['regions'][0]['id'] == 999 and result['regions'][0]['latency_ms'] is None


def test_config_only_returns_allowed_values():
    config = probe.read_config(CONFIG)
    assert config['enabled'] is True and config['region_id'] == 999
    assert config['has_urls'] is True and config['public_map'] is True
    assert 'secret-marker' not in json.dumps(config)
    assert probe.read_config(CONFIG.replace('enabled: true', 'enabled: false'))['enabled'] is False
    assert probe.read_config(CONFIG.split('  urls:')[0] + '  urls: []\n')['public_map'] is False


@pytest.mark.parametrize('config', [CONFIG.replace('enabled: true', 'enabled: *alias'),
                                    CONFIG.replace('enabled: true', 'enabled: true\n    enabled: false'), 'private: secret'])
def test_ambiguous_config_is_not_guessed(config):
    with pytest.raises(ValueError): probe.read_config(config)


@pytest.mark.parametrize('enabled,headscale,code', [(True, True, 200), (False, True, None), (True, True, 503), (None, False, None)])
def test_ssh_wire_allowlist(enabled, headscale, code):
    raw = {'state': 'ready', 'headscale': headscale, 'probe_code': code, 'secret': 'secret-marker',
           'config': {'enabled': enabled, 'region_id': 999, 'private_key': 'secret-marker'} if enabled is not None else None}
    result = parse_remote_derp('VPN_DERP_BEGIN\n' + json.dumps(raw) + '\nVPN_DERP_END\n')
    assert result['headscale'] == headscale and result['probe_code'] == code
    assert 'secret-marker' not in json.dumps(result)
    assert parse_remote_derp('missing python3') == {'state': 'unavailable'}


def test_collector_read_only_probe_and_port_owner(monkeypatch, tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text(CONFIG)
    monkeypatch.setattr(probe, 'Path', lambda _: path)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        assert 0 < kwargs['timeout'] <= 2.5
        if args[0] == 'ip': output = '[{"addr_info":[{"local":"8.8.8.8"}]}]'
        elif args[:3] == ['ss', '-H', '-tlpn']: output = 'LISTEN 0 10 *:443 *:* users:(("xray",pid=1,fd=1))'
        elif args[0] == 'ss': output = 'UNCONN 0 0 *:3478 *:*'
        elif args[0] == 'headscale': output = 'headscale version v0.28.0'
        elif args[0] == 'curl': output = '200'
        else: output = ''
        return SimpleNamespace(returncode=0, stdout=output)
    monkeypatch.setattr(probe.subprocess, 'run', run)
    result = probe.collect()
    assert result['tcp443_owner'] == 'xray' and result['tcp443_busy'] is True
    assert result['probe_code'] == 200 and result['stun_listening'] is True
    assert result['version'] == 'v0.28.0' and result['public_ipv4'] is True
    assert 'secret-marker' not in json.dumps(result)
    curl = next(args for args in calls if args[0] == 'curl')
    assert '--resolve' in curl and 'control.example.com:443:127.0.0.1' in curl
    assert '-k' not in curl and '--insecure' not in curl


def test_remote_probe_has_own_timeout_and_closes_channel(monkeypatch):
    service = SSHService()
    client, stdout = Mock(), Mock()
    stdout.read.return_value = b'VPN_DERP_BEGIN\n{"state":"ready"}\nVPN_DERP_END'
    client.exec_command.return_value = (Mock(), stdout, Mock())
    monkeypatch.setattr(service, 'get_connection_pooled', Mock(return_value=client))
    assert service.get_derp_snapshot('192.0.2.1', 'user', 'secret')['state'] == 'ready'
    assert client.exec_command.call_args.kwargs['timeout'] == 14
    stdout.read.assert_called_once_with(65537)
    stdout.channel.close.assert_called_once()


@pytest.mark.parametrize('output,state', [
    ('pong from demo (100.64.0.2) via DERP(ams) in 53ms', 'relay'),
    ('pong from demo (100.64.0.2) via 192.0.2.2:41641 in 3ms', 'direct'),
    ('pong from demo (100.64.0.2) via [2001:db8::1]:41641 in 3ms', 'direct'),
    ('pong from demo (100.64.0.2) via DERP(ams) in 53ms\npong from demo (100.64.0.2) via 192.0.2.2:41641 in 2ms', 'direct'),
    ('ping timed out', 'unknown'),
    ('pong from demo (100.64.0.2) via peer-relay(192.0.2.3) in 3ms', 'unknown'),
])
def test_only_ping_confirms_path_and_last_pong_wins(output, state):
    assert derp.parse_ping(output)['state'] == state


def test_ping_target_must_be_a_current_visible_peer(monkeypatch):
    monkeypatch.setattr(derp, 'tailscale_executable', lambda: 'tailscale')
    monkeypatch.setattr(derp, 'read_tailscale', lambda *a, **k: {'BackendState':'Running','Peer':{
        'key': {'ID':'visible','TailscaleIPs':['100.64.0.2']}}})
    run = Mock(return_value=SimpleNamespace(returncode=1, stdout='pong from demo (100.64.0.2) via DERP(ams) in 50ms'))
    monkeypatch.setattr(derp.subprocess, 'run', run)
    assert derp.check_peer_path('192.0.2.1; command')['state'] == 'unknown'
    run.assert_not_called()
    assert derp.check_peer_path('visible')['state'] == 'relay'
    assert run.call_args.args[0][-1] == '100.64.0.2'
    assert '--c=3' in run.call_args.args[0]
