window.PROJECT_STATE_CLASSES = {running: 'text-bg-success', partial: 'text-bg-warning',
    stopped: 'text-bg-danger', unknown: 'text-bg-secondary'};

window.renderProjectStats = function (root, projects) {
    if (!root) return;
    root.replaceChildren();
    const labels = root.dataset;
    const states = {active: labels.active, inactive: labels.inactive, failed: labels.failed, unknown: labels.unknown};
    const found = (projects || []).filter(project => project.state !== 'unknown');
    if (!found.length) {
        root.textContent = projects && projects.length ? labels.unknown : labels.none;
        return;
    }
    const metric = value => typeof value === 'number' && Number.isFinite(value);
    found.forEach(project => {
        const item = document.createElement('div');
        item.className = 'border-bottom py-2';
        const header = document.createElement('div');
        header.className = 'd-flex justify-content-between align-items-center flex-wrap gap-2';
        const name = document.createElement('strong');
        name.textContent = project.name;
        const badge = document.createElement('span');
        const active = project.components.filter(row => row.status === 'active').length;
        badge.className = 'badge ' + (PROJECT_STATE_CLASSES[project.state] || PROJECT_STATE_CLASSES.unknown);
        badge.textContent = `${labels[project.state] || labels.unknown} · ${active}/${project.components.length}`;
        header.append(name, badge);
        item.append(header);
        project.components.forEach(row => {
            const line = document.createElement('div');
            line.className = 'small mt-1 d-flex justify-content-between flex-wrap gap-2';
            const title = document.createElement('code');
            title.textContent = row.kind === 'container' ? `${row.name} (${labels.container})` : row.name;
            const details = document.createElement('span');
            details.className = row.status === 'active' ? 'text-body-secondary' : 'text-danger';
            const parts = [states[row.status] || labels.unknown];
            if (row.kind === 'unit' && row.status === 'active' && row.name.endsWith('.service')) {
                parts.push('CPU ' + (metric(row.cpu_percent) ? row.cpu_percent.toFixed(1) + '%' : '—'));
                parts.push(`${labels.memory} ` + (metric(row.memory_bytes) ? (row.memory_bytes / 1048576).toFixed(1) + ' MiB' : '—'));
                parts.push(`${labels.tasks} ` + (metric(row.tasks) ? row.tasks : '—'));
            }
            details.textContent = parts.join(' · ');
            line.append(title, details);
            item.append(line);
        });
        root.append(item);
    });
};
