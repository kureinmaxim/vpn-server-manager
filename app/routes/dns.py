"""DNS card: provider accounts, domains, registrars and records."""
import secrets

from cryptography.fernet import InvalidToken
from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   session, url_for)
from flask_babel import gettext as _, lazy_gettext as _l

from ..services import dns_registry as dns_reg, registry
from ..utils.credentials import sanitize_secret
from ..utils.decorators import csrf_protect

dns_bp = Blueprint('dns', __name__, url_prefix='/dns')

ERRORS = {
    'domain': _l('Введите корректное доменное имя, например example.com.'),
    'url': _l('Адрес должен начинаться с http:// или https://.'),
    'date': _l('Укажите дату в формате ГГГГ-ММ-ДД.'),
    'name': _l('Укажите название провайдера.'),
    'provider': _l('Выбранный DNS-провайдер не найден.'),
    'record': _l('Выберите поддерживаемый тип DNS-записи.'),
    'content': _l('Проверьте значение записи: для A нужен IPv4, для AAAA — IPv6.'),
    'duplicate': _l('Такой домен уже есть в списке.'),
    'no_file': _l('Нет активного файла данных. Добавьте сервер или импортируйте файл данных.'),
}


@dns_bp.before_request
def protect():
    if not (session.get('pin_authenticated') or (session.get('authenticated') and session.get('pin_verified'))):
        return redirect(url_for('main.index_locked'))
    session.setdefault('csrf_token', secrets.token_urlsafe(32))


def _manager():
    manager = registry.get('data_manager')
    if not manager:
        abort(503)
    return manager


def _load():
    try:
        return dns_reg.normalize(_manager().load_dns(current_app.config))
    except (InvalidToken, ValueError, OSError):
        abort(500)


def _save(dns):
    manager = _manager()
    path = manager.get_active_data_path(current_app.config)
    if not path:
        raise dns_reg.DnsError('no_file')
    manager.save_dns({} if dns_reg.is_empty(dns) else dns, path)


def _decrypted(provider):
    manager = _manager()
    return dict(provider, **{f + '_decrypted': sanitize_secret(manager.decrypt_data(provider.get(f, '')))
                             for f in dns_reg.SECRET_FIELDS})


def _domain_or_404(dns, domain_id):
    domain = dns_reg.find(dns['domains'], domain_id)
    if domain is None:
        abort(404)
    return domain


def _fail(exc):
    flash(str(ERRORS.get(exc.code, exc.code)), 'danger')


@dns_bp.get('/')
def index():
    dns = _load()
    providers = {p['id']: _decrypted(p) for p in dns['providers']}
    domains = sorted(dns['domains'], key=lambda d: d['name'])
    return render_template('dns/index.html', providers=list(providers.values()), provider_map=providers,
                           domains=domains, days_left=dns_reg.days_left, presets=dns_reg.PRESETS)


@dns_bp.route('/providers/new', methods=['GET', 'POST'])
@dns_bp.route('/providers/<provider_id>/edit', methods=['GET', 'POST'])
@csrf_protect
def provider_form(provider_id=None):
    dns = _load()
    current = dns_reg.find(dns['providers'], provider_id) if provider_id else None
    if provider_id and current is None:
        abort(404)
    if request.method == 'POST':
        try:
            provider = dns_reg.build_provider(request.form, current, _manager().encrypt_data)
            if current:
                dns['providers'][dns['providers'].index(current)] = provider
            else:
                dns['providers'].append(provider)
            _save(dns)
            flash(_('DNS-провайдер сохранён.'), 'success')
            return redirect(url_for('dns.index'))
        except dns_reg.DnsError as exc:
            _fail(exc)
    return render_template('dns/form.html', form='provider', item=_decrypted(current) if current else None,
                           presets=dns_reg.PRESETS, values=request.form if request.method == 'POST' else None)


@dns_bp.post('/providers/<provider_id>/delete')
@csrf_protect
def provider_delete(provider_id):
    dns = _load()
    provider = dns_reg.find(dns['providers'], provider_id)
    if provider is None:
        abort(404)
    dns['providers'].remove(provider)
    for domain in dns['domains']:
        if domain.get('provider_id') == provider_id:
            domain['provider_id'] = ''
    _save(dns)
    flash(_('DNS-провайдер удалён.'), 'success')
    return redirect(url_for('dns.index'))


@dns_bp.route('/domains/new', methods=['GET', 'POST'])
@dns_bp.route('/domains/<domain_id>/edit', methods=['GET', 'POST'])
@csrf_protect
def domain_form(domain_id=None):
    dns = _load()
    current = _domain_or_404(dns, domain_id) if domain_id else None
    if request.method == 'POST':
        try:
            domain = dns_reg.build_domain(request.form, current, dns['providers'])
            if any(d['name'] == domain['name'] and d is not current for d in dns['domains']):
                raise dns_reg.DnsError('duplicate')
            if current:
                dns['domains'][dns['domains'].index(current)] = domain
            else:
                dns['domains'].append(domain)
            _save(dns)
            flash(_('Домен сохранён.'), 'success')
            return redirect(url_for('dns.domain', domain_id=domain['id']))
        except dns_reg.DnsError as exc:
            _fail(exc)
    registrars = sorted({d['registrar'] for d in dns['domains'] if d.get('registrar')}
                        | {p['name'] for p in dns['providers']})
    return render_template('dns/form.html', form='domain', item=current, providers=dns['providers'],
                           registrars=registrars, values=request.form if request.method == 'POST' else None)


@dns_bp.post('/domains/<domain_id>/delete')
@csrf_protect
def domain_delete(domain_id):
    dns = _load()
    dns['domains'].remove(_domain_or_404(dns, domain_id))
    _save(dns)
    flash(_('Домен удалён.'), 'success')
    return redirect(url_for('dns.index'))


@dns_bp.get('/domains/<domain_id>')
def domain(domain_id):
    dns = _load()
    item = _domain_or_404(dns, domain_id)
    provider = dns_reg.find(dns['providers'], item.get('provider_id'))
    records = sorted(item['records'], key=lambda r: (r['name'] != '@', r['name'], r['type']))
    edit = dns_reg.find(item['records'], request.args.get('edit'))
    return render_template('dns/domain.html', domain=item, records=records, edit=edit,
                           provider=_decrypted(provider) if provider else None,
                           days_left=dns_reg.days_left(item), fqdn=dns_reg.record_fqdn,
                           record_types=dns_reg.RECORD_TYPES)


@dns_bp.post('/domains/<domain_id>/records')
@dns_bp.post('/domains/<domain_id>/records/<record_id>')
@csrf_protect
def record_save(domain_id, record_id=None):
    dns = _load()
    item = _domain_or_404(dns, domain_id)
    current = dns_reg.find(item['records'], record_id) if record_id else None
    if record_id and current is None:
        abort(404)
    try:
        record = dns_reg.build_record(request.form, item, current)
        if current:
            item['records'][item['records'].index(current)] = record
        else:
            item['records'].append(record)
        _save(dns)
        flash(_('Запись сохранена.'), 'success')
    except dns_reg.DnsError as exc:
        _fail(exc)
    return redirect(url_for('dns.domain', domain_id=domain_id) + '#records')


@dns_bp.post('/domains/<domain_id>/records/<record_id>/delete')
@csrf_protect
def record_delete(domain_id, record_id):
    dns = _load()
    item = _domain_or_404(dns, domain_id)
    record = dns_reg.find(item['records'], record_id)
    if record is None:
        abort(404)
    item['records'].remove(record)
    _save(dns)
    flash(_('Запись удалена.'), 'success')
    return redirect(url_for('dns.domain', domain_id=domain_id) + '#records')
