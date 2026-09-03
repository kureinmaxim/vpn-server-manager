"""Board order and archive flag for the server list."""

from app.utils.board import apply_archived, reorder_servers


def test_reorder_servers_follows_id_list_and_keeps_the_rest():
    servers = [{'id': 1, 'name': 'a'}, {'id': 2, 'name': 'b'}, {'id': 3, 'name': 'c'}]
    result = reorder_servers(servers, ['3', '1'])
    assert [s['id'] for s in result] == [3, 1, 2]


def test_reorder_servers_ignores_unknown_ids():
    servers = [{'id': 10}, {'id': 20}]
    result = reorder_servers(servers, [99, 20, 10])
    assert [s['id'] for s in result] == [20, 10]


def test_apply_archived_sets_boolean():
    server = {'id': 1, 'archived': False}
    apply_archived(server, True)
    assert server['archived'] is True
    apply_archived(server, False)
    assert server['archived'] is False
