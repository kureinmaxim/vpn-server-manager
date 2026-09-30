(() => {
    'use strict';
    // Click a column header to sort; click again to reverse. Each table sorts on its own.
    const collator = new Intl.Collator(undefined, {numeric: true, sensitivity: 'base'});
    document.querySelectorAll('.dns-sortable').forEach(table => {
        table.querySelectorAll('.dns-sort').forEach(button => button.addEventListener('click', () => {
            const th = button.closest('th');
            const ascending = th.getAttribute('aria-sort') !== 'ascending';
            table.querySelectorAll('th[aria-sort]').forEach(cell => cell.setAttribute('aria-sort', 'none'));
            th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
            const col = Number(button.dataset.col);
            const body = table.tBodies[0];
            const rows = [...body.rows].sort((a, b) =>
                collator.compare(a.cells[col].dataset.sort, b.cells[col].dataset.sort) * (ascending ? 1 : -1));
            body.append(...rows);
        }));
    });
})();
