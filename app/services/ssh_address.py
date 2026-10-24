"""Card addresses for SSH: the main ip_address, then extra addresses (mesh, LAN, direct) in order.

All addresses share the card's SSH port and credentials. The first one that accepts a TCP
connection on that port is used and remembered until the app restarts.
"""
import re
import socket
import threading

LABELS = ('mesh', 'lan', 'direct')
MAX_EXTRA = 4
# Hostnames, IPv4 and IPv6: passed to socket/paramiko only, never to a shell.
_ADDRESS = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9.:-]{0,251}[A-Za-z0-9])?')
PROBE_TIMEOUT = 2.0

_last_good = {}
_lock = threading.Lock()


class AddressError(ValueError):
    pass


def clean_addresses(rows, main=''):
    """Validated extra addresses; empty rows and duplicates of the main address are dropped."""
    if not isinstance(rows, (list, tuple)):
        return []
    result, seen = [], {str(main or '').strip().lower()}
    for row in rows:
        if not isinstance(row, dict):
            continue
        address = str(row.get('address') or '').strip()
        if not address:
            continue
        if not _ADDRESS.fullmatch(address):
            raise AddressError(address)
        if address.lower() in seen:
            continue
        seen.add(address.lower())
        label = row.get('label') if row.get('label') in LABELS else 'direct'
        result.append({'address': address, 'label': label})
    if len(result) > MAX_EXTRA:
        raise AddressError('too many')
    return result


def card_addresses(server):
    """Main address first, then the extra ones in their saved order."""
    main = str(server.get('ip_address') or server.get('ip') or '').strip()
    try:
        extra = [row['address'] for row in clean_addresses(server.get('extra_addresses') or [], main)]
    except AddressError:
        extra = []
    return ([main] if main else []) + extra


def _reachable(address, port, timeout):
    try:
        socket.create_connection((address, int(port)), timeout=timeout).close()
        return True
    except (OSError, ValueError):
        return False


def ssh_address(server, port=22, timeout=PROBE_TIMEOUT):
    """Address to connect to. A single address is returned without probing."""
    addresses = card_addresses(server)
    if len(addresses) <= 1:
        return addresses[0] if addresses else ''
    key = str(server.get('id'))
    with _lock:
        last = _last_good.get(key)
    order = ([last] if last in addresses else []) + [a for a in addresses if a != last]
    for address in order:
        if _reachable(address, port, timeout):
            with _lock:
                _last_good[key] = address
            return address
    # Nothing answered: keep the main address so the usual error is reported.
    return addresses[0]


def forget(server_id=None):
    """Drop remembered choices (after the card is edited, or in tests)."""
    with _lock:
        if server_id is None:
            _last_good.clear()
        else:
            _last_good.pop(str(server_id), None)
