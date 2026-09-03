"""Server list board: drag order and archive (dim) flag."""
from __future__ import annotations


def reorder_servers(servers: list, ordered_ids) -> list:
    """Return servers in ordered_ids sequence; leftover items keep original order at the end."""
    by_id = {str(server.get('id')): server for server in servers}
    result = []
    seen = set()
    for raw_id in ordered_ids or []:
        key = str(raw_id)
        if key in by_id and key not in seen:
            result.append(by_id[key])
            seen.add(key)
    for server in servers:
        key = str(server.get('id'))
        if key not in seen:
            result.append(server)
            seen.add(key)
    return result


def apply_archived(server: dict, archived: bool) -> dict:
    """Mark a server card as archival (dim on the list) or active."""
    server['archived'] = bool(archived)
    return server
