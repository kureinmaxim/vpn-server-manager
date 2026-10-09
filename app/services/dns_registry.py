"""DNS registry: DNS-provider accounts, domains and their records.

Stored inside the encrypted servers file under the "dns" key:
{"providers": [...], "domains": [{..., "records": [...]}]}.
Provider logins and passwords are additionally Fernet-encrypted, as for servers.
"""
import datetime
import ipaddress
import re
import secrets

PRESETS = {
    'cloudflare': ('Cloudflare', 'https://dash.cloudflare.com/login'),
    'namecheap': ('Namecheap', 'https://www.namecheap.com/myaccount/login/'),
    'godaddy': ('GoDaddy', 'https://sso.godaddy.com/'),
    'porkbun': ('Porkbun', 'https://porkbun.com/account/login'),
    'regru': ('REG.RU', 'https://www.reg.ru/user/authorize'),
    'route53': ('Amazon Route 53', 'https://console.aws.amazon.com/route53/'),
    'other': ('', ''),
}
RECORD_TYPES = ('A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA', 'PTR')
SECRET_FIELDS = ('user', 'password')
ROLES = ('auto', 'main', 'service')
# Hosts that cPanel and mail autoconfiguration create automatically
SERVICE_HOSTS = {'autoconfig', 'autodiscover', 'cpanel', 'cpcalendars', 'cpcontacts', 'webdisk', 'webmail',
                 'whm', 'ftp', 'mail', 'imap', 'pop', 'smtp'}
SERVICE_TYPES = {'MX', 'TXT', 'SRV', 'NS', 'CAA', 'PTR'}
_SHARED = (ipaddress.ip_network('100.64.0.0/10'),)
_LABEL = re.compile(r'(?!-)[a-z0-9_-]{1,63}(?<!-)')


class DnsError(ValueError):
    """Validation error; code maps to a localized message in the route."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def new_id():
    return secrets.token_hex(6)


def clean_domain(value, allow_wildcard=False):
    name = (value or '').strip().lower().rstrip('.')
    try:
        name = name.encode('idna').decode('ascii')
    except UnicodeError:
        raise DnsError('domain')
    labels = name.split('.')
    if allow_wildcard and labels[0] == '*':
        labels = labels[1:]
    if len(name) > 253 or len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels):
        raise DnsError('domain')
    return name


def clean_url(value):
    url = (value or '').strip()
    if url and not re.fullmatch(r'https?://[^\s"<>]+', url, re.I):
        raise DnsError('url')
    return url


def clean_date(value):
    value = (value or '').strip()
    if value:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise DnsError('date')
    return value


def normalize(dns):
    dns = dns if isinstance(dns, dict) else {}
    providers = [p for p in dns.get('providers') or [] if isinstance(p, dict) and p.get('id')]
    domains = [d for d in dns.get('domains') or [] if isinstance(d, dict) and d.get('id')]
    for domain in domains:
        domain['records'] = [r for r in domain.get('records') or [] if isinstance(r, dict) and r.get('id')]
    return {'providers': providers, 'domains': domains}


def is_empty(dns):
    return not (dns.get('providers') or dns.get('domains'))


def find(items, item_id):
    return next((item for item in items if item.get('id') == item_id), None)


def record_fqdn(record, domain):
    name = record.get('name') or '@'
    return domain['name'] if name == '@' else f"{name}.{domain['name']}"


def build_provider(form, current, encrypt):
    kind = form.get('kind', 'other')
    if kind not in PRESETS:
        kind = 'other'
    title, preset_url = PRESETS[kind]
    name = (form.get('name') or '').strip()[:80] or title
    if not name:
        raise DnsError('name')
    provider = dict(current or {'id': new_id()})
    provider.update(kind=kind, name=name, notes=(form.get('notes') or '').strip()[:2000],
                    login_url=clean_url(form.get('login_url')) or preset_url)
    for field in SECRET_FIELDS:
        value = form.get(field) or ''
        if value:
            provider[field] = encrypt(value)
        elif form.get('clear_' + field) or field not in provider:
            provider[field] = ''
    return provider


def build_domain(form, current, providers):
    domain = dict(current or {'id': new_id(), 'records': []})
    provider_id = form.get('provider_id') or ''
    if provider_id and not find(providers, provider_id):
        raise DnsError('provider')
    domain.update(
        name=clean_domain(form.get('name')),
        provider_id=provider_id,
        registrar=(form.get('registrar') or '').strip()[:120],
        registrar_url=clean_url(form.get('registrar_url')),
        registered_on=clean_date(form.get('registered_on')),
        expires_on=clean_date(form.get('expires_on')),
        auto_renew=bool(form.get('auto_renew')),
        notes=(form.get('notes') or '').strip()[:2000],
    )
    return domain


def auto_role(record):
    """Records created by mail, cPanel or domain verification are 'service'; the rest are 'main'."""
    name = record.get('name') or '@'
    if record.get('type') in SERVICE_TYPES or any(label.startswith('_') for label in name.split('.')):
        return 'service'
    return 'service' if name in SERVICE_HOSTS else 'main'


def role(record):
    chosen = record.get('role', 'auto')
    return chosen if chosen in ('main', 'service') else auto_role(record)


def address_scope(record):
    """'private' for LAN/Tailscale (CGNAT) addresses in A/AAAA records, else ''."""
    if record.get('type') not in ('A', 'AAAA'):
        return ''
    try:
        address = ipaddress.ip_address(record.get('content', ''))
    except ValueError:
        return ''
    return 'private' if address.is_private or any(address in net for net in _SHARED) else ''


def build_record(form, domain, current=None):
    record_type = (form.get('type') or '').upper()
    if record_type not in RECORD_TYPES:
        raise DnsError('record')
    name = (form.get('name') or '').strip().lower().rstrip('.')
    suffix = '.' + domain['name']
    if name == domain['name'] or name in ('', '@'):
        name = '@'
    else:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
        clean_domain(name + suffix, allow_wildcard=True)
    content = (form.get('content') or '').strip()
    if not content or len(content) > 2048:
        raise DnsError('content')
    if record_type in ('A', 'AAAA'):
        try:
            address = ipaddress.ip_address(content)
        except ValueError:
            raise DnsError('content')
        if address.version != (4 if record_type == 'A' else 6):
            raise DnsError('content')
    record = dict(current or {'id': new_id()})
    record.update(name=name, type=record_type, content=content,
                  proxied=bool(form.get('proxied')) and record_type in ('A', 'AAAA', 'CNAME'),
                  notes=(form.get('notes') or '').strip()[:500],
                  role=form.get('role') if form.get('role') in ROLES else record.get('role', 'auto'))
    return record


def days_left(domain, today=None):
    if not domain.get('expires_on'):
        return None
    return (datetime.date.fromisoformat(domain['expires_on']) - (today or datetime.date.today())).days


def host_choices(dns):
    """Domain names and record FQDNs for host pickers (e.g. Net Tools)."""
    names = []
    for domain in normalize(dns)['domains']:
        names.append(domain['name'])
        names.extend(record_fqdn(r, domain) for r in domain['records']
                     if role(r) == 'main' and not r['name'].startswith('*'))
    return sorted(set(names), key=lambda n: (n.split('.')[-2:], n.count('.'), n))


def records_for_ip(dns, ip):
    """A/AAAA records pointing at ip, plus CNAMEs that reach them (marked with 'via')."""
    ip = (ip or '').strip()
    if not ip:
        return []
    direct, fqdns = [], set()
    domains = normalize(dns)['domains']
    for domain in domains:
        for record in domain['records']:
            if record['type'] in ('A', 'AAAA') and record['content'] == ip:
                direct.append({'domain': domain, 'record': record, 'fqdn': record_fqdn(record, domain), 'via': None})
                fqdns.add(record_fqdn(record, domain))
    linked = []
    for domain in domains:
        for record in domain['records']:
            target = record['content'].rstrip('.').lower()
            if record['type'] == 'CNAME' and target in fqdns:
                linked.append({'domain': domain, 'record': record, 'fqdn': record_fqdn(record, domain), 'via': target})
    key = lambda item: (item['domain']['name'], role(item['record']) != 'main', item['fqdn'])
    return sorted(direct, key=key) + sorted(linked, key=key)


def move_records(dns, old_ip, new_ip, record_ids):
    """Points the selected A/AAAA records from old_ip to new_ip; returns how many changed."""
    new_ip = ipaddress.ip_address(new_ip)
    changed = 0
    for item in records_for_ip(dns, old_ip):
        record = item['record']
        if item['via'] is None and record['id'] in record_ids \
                and (record['type'] == 'A') == (new_ip.version == 4):
            record['content'] = str(new_ip)
            changed += 1
    return changed


_ZONE_LINE = re.compile(r'^(\S+)\s+(?:(\d+)\s+)?(?:IN\s+)?([A-Za-z]+)\s+(.*)$')


def _zone_value(rtype, raw):
    body, sep, tags = raw.rpartition(' ; cf_tags=')
    if not sep:
        body, tags = raw, ''
    if rtype == 'TXT':
        # Long TXT values are split into several quoted strings
        value = ''.join(re.findall(r'"((?:[^"\\]|\\.)*)"', body)) or body.strip()
    else:
        value = body.strip()
        if rtype in ('CNAME', 'MX', 'SRV', 'NS', 'PTR'):
            value = ' '.join(part.rstrip('.') for part in value.split())
    return value, 'cf-proxied:true' in tags


def zone_domain(text):
    """Domain of a zone file: the ';; Domain:' header or the SOA owner."""
    for line in text.splitlines():
        match = re.match(r';;\s*Domain:\s*(\S+)', line) or re.match(r'(\S+)\s+(?:\d+\s+)?(?:IN\s+)?SOA\s', line)
        if match:
            return clean_domain(match.group(1))
    raise DnsError('zone')


def add_zone_records(domain, records):
    """Adds records that are not present yet (same name, type and value); returns the count."""
    existing = {(r['name'], r['type'], r['content']) for r in domain['records']}
    added = [r for r in records if (r['name'], r['type'], r['content']) not in existing]
    domain['records'].extend(added)
    return len(added)


def replace_zone_records(domain, records):
    """Makes the domain's records match a zone file; returns (added, removed, kept).

    A record with the same name, type and value as one in the file is kept as is
    (id, group and note stay; only the Cloudflare proxy flag is refreshed). Records
    missing from the file are removed. Domain fields — provider, registrar, dates —
    are not touched.
    """
    incoming = {}
    for record in records:
        incoming.setdefault((record['name'], record['type'], record['content']), record)
    kept, removed = [], 0
    for record in domain['records']:
        match = incoming.pop((record['name'], record['type'], record['content']), None)
        if match is None:
            removed += 1
            continue
        record['proxied'] = match['proxied']
        kept.append(record)
    domain['records'] = kept + list(incoming.values())
    return len(incoming), removed, len(kept)


def parse_zone(text, domain):
    """Records from a BIND zone file (Cloudflare "Export"); SOA and apex NS are skipped."""
    records, skipped = [], 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        match = _ZONE_LINE.match(line)
        if not match:
            skipped += 1
            continue
        owner, _, rtype, rest = match.groups()
        rtype = rtype.upper()
        name = owner.rstrip('.').lower()
        if rtype == 'SOA' or (rtype == 'NS' and name == domain['name']):
            continue
        content, proxied = _zone_value(rtype, rest)
        try:
            records.append(build_record({'name': name, 'type': rtype, 'content': content,
                                         'proxied': proxied}, domain))
        except DnsError:
            skipped += 1
    return records, skipped


def merge(current, incoming, reencrypt):
    """Adds providers and domains from an imported file; existing names win."""
    current, incoming = normalize(current), normalize(incoming)
    provider_ids = {}
    by_name = {p['name'].lower(): p for p in current['providers']}
    for provider in incoming['providers']:
        existing = by_name.get(provider.get('name', '').lower())
        if existing:
            provider_ids[provider['id']] = existing['id']
            continue
        added_provider = dict(provider, id=new_id())
        for field in SECRET_FIELDS:
            if added_provider.get(field):
                added_provider[field] = reencrypt(added_provider[field])
        provider_ids[provider['id']] = added_provider['id']
        current['providers'].append(added_provider)
        by_name[added_provider['name'].lower()] = added_provider
    names = {d['name'] for d in current['domains']}
    added = 0
    for domain in incoming['domains']:
        if domain.get('name') in names:
            continue
        current['domains'].append(dict(domain, id=new_id(), provider_id=provider_ids.get(domain.get('provider_id'), '')))
        names.add(domain.get('name'))
        added += 1
    return current, added
