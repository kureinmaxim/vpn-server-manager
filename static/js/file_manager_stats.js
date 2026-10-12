window.renderFileManagerStats = function (root, rows) {
    if (!root) return;
    root.replaceChildren();
    const labels = root.dataset;
    const states = {active: labels.active, inactive: labels.inactive,
        failed: labels.failed, not_installed: labels.missing, unknown: labels.unknown};
    if (!rows || !rows.length) {
        root.textContent = labels.unknown;
        return;
    }
    const metric = value => typeof value === 'number' && Number.isFinite(value);
    rows.forEach(row => {
        const item = document.createElement('div');
        item.className = 'border-bottom py-2';
        const header = document.createElement('div');
        header.className = 'd-flex justify-content-between flex-wrap gap-2';
        const name = document.createElement('strong');
        name.textContent = row.display_name;
        const status = document.createElement('span');
        status.className = 'small text-muted';
        status.textContent = states[row.status] || labels.unknown;
        header.append(name, status);
        const resources = document.createElement('div');
        resources.className = 'small mt-1';
        const cpu = metric(row.cpu_percent) ? row.cpu_percent.toFixed(1) + '%' : '—';
        const memory = metric(row.memory_bytes) ? (row.memory_bytes / 1048576).toFixed(1) + ' MiB' : '—';
        const tasks = metric(row.tasks) ? row.tasks : '—';
        resources.textContent = `CPU: ${cpu} · ${labels.memory}: ${memory} · ${labels.tasks}: ${tasks}`;
        item.append(header, resources);
        root.append(item);
    });
};
