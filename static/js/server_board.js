(function () {
    'use strict';

    var LABELS = window.SERVER_BOARD_I18N || {};
    var INTERACTIVE = 'a, button, input, textarea, select, form, label, .accordion-button';

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

    function applyArchived(card, archived) {
        if (!card) return;
        card.classList.toggle('is-archived', archived);
        var button = card.querySelector('.js-archive-toggle');
        if (!button) return;
        button.setAttribute('data-archived', archived ? '1' : '0');
        button.title = archived ? (LABELS.unarchive || '') : (LABELS.archive || '');
        var icon = button.querySelector('i');
        if (icon) {
            icon.className = archived ? 'bi bi-archive-fill' : 'bi bi-archive';
        }
    }

    function setExpanded(item, expanded) {
        var card = item.querySelector('.server-preview-card');
        if (!card) return;
        card.classList.toggle('is-expanded', expanded);
        item.classList.toggle('is-expanded', expanded);
        item.classList.toggle('col-sm-6', !expanded);
        item.classList.toggle('col-sm-12', expanded);
        item.classList.toggle('col-lg-4', !expanded);
        item.classList.toggle('col-xl-3', !expanded);
        item.classList.toggle('col-lg-6', expanded);
        item.classList.toggle('col-xl-6', expanded);
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
                        applyArchived(button.closest('.server-preview-card'), data.archived);
                    })
                    .catch(function (err) {
                        console.error('archive toggle failed', err);
                    });
            });
        });
    }

    function bindCardDblClick() {
        document.querySelectorAll('.server-preview-card').forEach(function (card) {
            if (card.dataset.boundDbl === '1') return;
            card.dataset.boundDbl = '1';
            card.addEventListener('dblclick', function (event) {
                if (event.target.closest(INTERACTIVE)) return;
                var selection = window.getSelection && window.getSelection();
                if (selection && String(selection).length > 0) return;
                var item = card.closest('.server-board-item');
                if (!item) return;
                event.preventDefault();
                if (card.classList.contains('is-archived')) {
                    var id = item.getAttribute('data-server-id');
                    postJson('/api/servers/' + encodeURIComponent(id) + '/archived', { archived: false })
                        .then(function (data) {
                            if (data && data.success) applyArchived(card, false);
                        })
                        .catch(function (err) {
                            console.error('unarchive on dblclick failed', err);
                        });
                    return;
                }
                setExpanded(item, !card.classList.contains('is-expanded'));
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
        bindCardDblClick();
        bindSortable();
    });
})();
