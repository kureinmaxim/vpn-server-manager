window.PROJECT_STATE_CLASSES = {running: 'text-bg-success', partial: 'text-bg-warning',
    stopped: 'text-bg-danger', unknown: 'text-bg-secondary'};

window.renderProjectStats = function (root, projects, diagnosticsUrl) {
    if (!root) return;
    root.replaceChildren();
    const labels = root.dataset;
    const states = {active: labels.active, inactive: labels.inactive, failed: labels.failed,
        unknown: labels.unknown, not_installed: labels.notInstalled};
    const found = projects || [];
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
        const core = project.components.filter(row => !row.optional);
        const active = core.filter(row => row.status === 'active').length;
        badge.className = 'badge ' + (PROJECT_STATE_CLASSES[project.state] || PROJECT_STATE_CLASSES.unknown);
        badge.textContent = `${labels[project.state] || labels.unknown} · ${active}/${core.length}`;
        header.append(name, badge);
        item.append(header);
        if (project.discovery) {
            const note = document.createElement('p');
            note.className = 'small text-body-secondary mb-1';
            note.textContent = project.detected ? labels.detected : labels.unavailable;
            if (project.detected && project.coverage === 'partial') note.textContent += ' · ' + labels.coverage;
            if (project.last_check) {
                const last = project.last_check;
                note.textContent = labels.functional + ': ' + (labels[last.state] || labels.unknown)
                    + ' · ' + labels.source + ' · ' + new Date(last.checked_at).toLocaleString();
                if (last.stale) note.textContent += ' · ' + labels.stale;
            }
            item.append(note);
            if (diagnosticsUrl) {
                const link = document.createElement('a'); link.className = 'small';
                link.href = diagnosticsUrl + '?role=' + encodeURIComponent(project.key);
                link.textContent = labels.diagnostics; item.append(link);
            }
        }
        project.components.forEach(row => {
            const line = document.createElement('div');
            line.className = 'small mt-1 d-flex justify-content-between flex-wrap gap-2';
            const title = document.createElement('code');
            const kinds = {container: labels.container, process: labels.process};
            title.textContent = kinds[row.kind] ? `${row.name} (${kinds[row.kind]})` : row.name;
            const details = document.createElement('span');
            details.className = row.status === 'active' ? 'text-body-secondary' : 'text-danger';
            const parts = [states[row.status] || labels.unknown];
            if (row.optional) parts.push(labels.optional);
            if (row.version) parts.push(row.version);
            if (row.compose_service) parts.push('Compose: ' + row.compose_service);
            if (row.ports) parts.push(row.ports);
            if (row.kind === 'unit' && row.status === 'active' && row.name.endsWith('.service')) {
                parts.push('CPU ' + (metric(row.cpu_percent) ? row.cpu_percent.toFixed(1) + '%' : '—'));
                parts.push(`${labels.memory} ` + (metric(row.memory_bytes) ? (row.memory_bytes / 1048576).toFixed(1) + ' MiB' : '—'));
                parts.push(`${labels.tasks} ` + (metric(row.tasks) ? row.tasks : '—'));
            }
            if (row.kind === 'process' && metric(row.count)) parts.push(`${labels.count}: ${row.count}`);
            details.textContent = parts.join(' · ');
            line.append(title, details);
            item.append(line);
        });
        root.append(item);
    });
};
