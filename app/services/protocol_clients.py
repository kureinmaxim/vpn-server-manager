"""Read existing TelegramOnly clients and explicitly export selected profiles.

URI field mappings follow TelegramOnly fcfa15a (MIT; see docs/third-party).
No bot imports: importing its managers can reconcile or modify host settings.
"""
import hashlib
import ipaddress
import re
import uuid
from urllib.parse import quote, urlencode

from .protocol_inspection import PROTOCOL_FILES, sources, read_metadata

EXPORT_PROTOCOLS = ('anytls', 'tuic', 'xhttp', 'mtproto', 'vless', 'hysteria2', 'naiveproxy', 'mieru')


def source_id(path):
    return hashlib.sha256(path.encode('utf-8')).hexdigest()


def selected_config(body, inventory, run):
    component = body.get('component')
    if component not in PROTOCOL_FILES:
        raise ValueError('invalid_operation')
    candidates = sources(inventory, run)[component]
    paths = {path for path, owner in candidates if source_id(path) == body.get('source_id')}
    if len(paths) != 1:
        raise ValueError('target_changed')
    data, revision = read_metadata(paths.pop())
    if revision != body.get('revision'):
        raise ValueError('target_changed')
    clients = data.get('clients', [])
    if component == 'naiveproxy':
        # NaiveProxy has one shared account, not a Telegram client list.
        clients = [{'name': data.get('username') or 'NaiveProxy',
                    'password': data.get('password')}]
    elif component == 'hysteria2' and not clients and data.get('password'):
        clients = [{'name': '', 'password': data['password']}]
    if not isinstance(clients, list) or len(clients) > 10000:
        raise ValueError('invalid_operation')
    return data, clients, revision


def client_operation(body, inventory, run):
    data, clients, revision = selected_config(body, inventory, run)
    component = body['component']
    if body['operation'] == 'clients':
        return {'clients': [{'index': index, 'name': str(client.get('name') or ('#' + str(index + 1)))[:200],
                             'exportable': component in EXPORT_PROTOCOLS}
                            for index, client in enumerate(clients) if isinstance(client, dict)],
                'revision': revision, 'export_supported': component in EXPORT_PROTOCOLS}
    index = body.get('index')
    if type(index) is not int or index < 0 or index >= len(clients) or not isinstance(clients[index], dict):
        raise ValueError('target_changed')
    return {'profile': export_profile(component, data, clients[index]), 'format': 'uri'}


def required_text(value):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise ValueError('invalid_profile')
    return value


def endpoint(config):
    server = required_text(config.get('server'))
    port = config.get('port', 443)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid_profile')
    try:
        address = ipaddress.ip_address(server)
        host = '[' + server + ']' if address.version == 6 else server
    except ValueError:
        host = server.encode('idna').decode('ascii')
        if len(host) > 253 or any(not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', label)
                                  for label in host.rstrip('.').split('.')):
            raise ValueError('invalid_profile')
    return host, port


def export_profile(component, config, client):
    if component not in EXPORT_PROTOCOLS:
        raise ValueError('unsupported_profile')
    host, port = endpoint(dict(config, server=config.get('domain') or config.get('server')) if component == 'naiveproxy' else config)
    params = {}
    if config.get('sni'):
        params['sni'] = required_text(config['sni'])
    title = quote(str(client.get('name') or component), safe='')
    if component == 'naiveproxy':
        scheme = config.get('scheme', 'https')
        if scheme not in ('https', 'quic'):
            raise ValueError('unsupported_profile')
        user = quote(required_text(config.get('username')), safe='')
        password = quote(required_text(config.get('password')), safe='')
        return f'naive+{scheme}://{user}:{password}@{host}:{port}#{title}'
    if component == 'mieru':
        pairs = [('profile', client.get('name') or 'Mieru'),
                 ('mtu', str(config.get('mtu', 1400))),
                 ('multiplexing', config.get('multiplexing', 'MULTIPLEXING_LOW')),
                 ('handshake-mode', config.get('handshake_mode', 'HANDSHAKE_STANDARD'))]
        bindings = config.get('port_bindings')
        if not isinstance(bindings, list) or not bindings or len(bindings) > 64:
            raise ValueError('invalid_profile')
        for binding in bindings:
            if not isinstance(binding, dict) or binding.get('protocol') not in ('TCP', 'UDP'):
                raise ValueError('invalid_profile')
            binding_port = binding.get('port')
            if type(binding_port) is int and 1 <= binding_port <= 65535:
                encoded_port = str(binding_port)
            else:
                span = binding.get('portRange')
                if isinstance(span, dict):
                    low, high = span.get('from'), span.get('to')
                elif isinstance(span, str) and re.fullmatch(r'\d{1,5}-\d{1,5}', span):
                    low, high = map(int, span.split('-'))
                else:
                    raise ValueError('invalid_profile')
                if type(low) is not int or type(high) is not int or not 1 <= low <= high <= 65535:
                    raise ValueError('invalid_profile')
                encoded_port = f'{low}-{high}'
            pairs.extend([('port', encoded_port), ('protocol', binding['protocol'])])
        for _, value in pairs: required_text(value)
        user = quote(required_text(client.get('name')), safe='')
        password = quote(required_text(client.get('password')), safe='')
        return f'mierus://{user}:{password}@{host}?' + urlencode(pairs, quote_via=quote) + '#' + title
    if component == 'hysteria2':
        auth = quote(required_text(client.get('password')), safe='')
        if config.get('clients'):
            auth = quote(required_text(client.get('name')), safe='') + ':' + auth
        params['sni'] = required_text(config.get('sni') or 'yahoo.com')
        if config.get('insecure') is True: params['insecure'] = '1'
        if config.get('obfs_type'):
            if config['obfs_type'] != 'salamander': raise ValueError('unsupported_profile')
            params.update(obfs='salamander', **{'obfs-password': required_text(config.get('obfs_password'))})
        return f'hy2://{auth}@{host}:{port}/?' + urlencode(params, quote_via=quote) + '#' + title
    if component == 'vless':
        auth = str(uuid.UUID(required_text(client.get('uuid'))))
        if config.get('transport', 'tcp') != 'tcp' or config.get('security', 'reality') != 'reality':
            raise ValueError('unsupported_profile')
        public_key = required_text(config.get('public_key'))
        short_id = config.get('short_id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', public_key) or not isinstance(short_id, str) or not re.fullmatch(r'(?:[a-fA-F0-9]{2}){0,8}', short_id):
            raise ValueError('invalid_profile')
        params.update(security='reality', encryption='none', pbk=public_key,
                      fp=required_text(config.get('fingerprint', 'chrome')), type='tcp',
                      flow=config.get('flow', 'xtls-rprx-vision'),
                      sni=required_text(config.get('sni') or 'www.microsoft.com'), sid=short_id)
        if params['flow'] not in ('', 'xtls-rprx-vision'): raise ValueError('unsupported_profile')
        return f'vless://{auth}@{host}:{port}?' + urlencode(params, quote_via=quote) + '#' + title
    if component == 'mtproto':
        secret = required_text(client.get('secret'))
        if not re.fullmatch(r'(?:[0-9a-fA-F]{32}|dd[0-9a-fA-F]{32}|ee[0-9a-fA-F]{34,})', secret) or len(secret) % 2:
            raise ValueError('invalid_profile')
        return 'tg://proxy?' + urlencode({'server': config['server'], 'port': config.get('port', 993), 'secret': secret})
    if component == 'anytls':
        auth = quote(required_text(client.get('password')), safe='')
        if config.get('insecure') is True:
            params['insecure'] = '1'
        scheme = 'anytls'
    else:
        auth = str(uuid.UUID(required_text(client.get('uuid'))))
        if component == 'tuic':
            scheme = 'tuic'
            auth += ':' + quote(required_text(client.get('password')), safe='')
            params.update(congestion_control=config.get('congestion_control', 'bbr'), udp_relay_mode=config.get('udp_relay_mode', 'native'))
            alpn = config.get('alpn', ['h3'])
            if not isinstance(alpn, list) or not all(isinstance(v, str) for v in alpn):
                raise ValueError('invalid_profile')
            params['alpn'] = ','.join(alpn)
            if config.get('insecure') is True:
                params['allow_insecure'] = '1'
        else:
            scheme = 'vless'
            security = config.get('security', 'tls')
            if security not in ('tls', 'none'):
                raise ValueError('unsupported_profile')
            params.update(type='xhttp', security=security, path=config.get('path', '/'), mode=config.get('mode', 'auto'))
            if config.get('host'):
                params['host'] = required_text(config['host'])
            if config.get('insecure') is True:
                params['allowInsecure'] = '1'
    for value in params.values():
        required_text(value)
    query = urlencode(params, quote_via=quote)
    return f'{scheme}://{auth}@{host}:{port}' + ('?' + query if query else '') + '#' + title
