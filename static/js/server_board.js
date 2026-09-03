(function () {
    'use strict';

    var LABELS = window.SERVER_BOARD_I18N || {};

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(body)
        }).then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
        });
    }

    function bindArchiveToggles() {
        document.querySelectorAll('.js-archive-toggle').forEach(function (button) {
            if (button.dataset.boundArchive === '1') return;
            button.dataset.boundArchive = '1';
            button.addEventListener('click', function (event) {
                event.preventDefault();
                event.stopPropagation();
                var id = button.getAttribute('data-server-id');
                var next = button.getAttribute('data-archived') !== '1';
                postJson('/api/servers/' + encodeURIComponent(id) + '/archived', { archived: next })
                    .then(function (data) {
                        if (!data || !data.success) return;
                        var card = button.closest('.server-preview-card');
                        if (card) card.classList.toggle('is-archived', data.archived);
                        button.setAttribute('data-archived', data.archived ? '1' : '0');
                        button.title = data.archived ? (LABELS.unarchive || '') : (LABELS.archive || '');
                        var icon = button.querySelector('i');
                        if (icon) {
                            icon.className = data.archived ? 'bi bi-archive-fill' : 'bi bi-archive';
                        }
                    })
                    .catch(function (err) {
                        console.error('archive toggle failed', err);
                    });
            });
        });
    }

    function bindSortable() {
        var board = document.getElementById('server-board');
        if (!board || typeof Sortable === 'undefined') return;
        Sortable.create(board, {
            animation: 150,
            handle: '.server-card-handle',
            draggable: '.server-board-item',
            ghostClass: 'server-board-ghost',
            onEnd: function () {
                var order = Array.prototype.map.call(
                    board.querySelectorAll('.server-board-item'),
                    function (el) { return el.getAttribute('data-server-id'); }
                );
                postJson('/api/servers/reorder', { order: order }).catch(function (err) {
                    console.error('reorder failed', err);
                });
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        bindArchiveToggles();
        bindSortable();
    });
})();
