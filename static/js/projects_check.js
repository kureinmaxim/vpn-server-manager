(function () {
    const modal = document.getElementById('projectsCheckModal');
    const config = window.PROJECTS_CHECK_CONFIG;
    if (!modal || !config) return;
    const t = config.i18n;
    const body = document.getElementById('projects-check-rows');
    const progress = document.getElementById('projects-check-progress');
    const absent = document.getElementById('projects-check-absent');
    const errors = document.getElementById('projects-check-errors');
    const refresh = document.getElementById('projects-check-refresh');
    const locale = document.documentElement.lang || undefined;
    let run = null;
    let servers = [];
    let completedAt = null;

    async function getJSON(url, pass, timeout = 30000) {
        const controller = new AbortController();
        const cancel = () => controller.abort();
        pass.signal.addEventListener('abort', cancel, {once: true});
        let timedOut = false;
        const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
        try {
            const response = await fetch(url, {signal: controller.signal, cache: 'no-store', headers: {'Accept': 'application/json'}});
            if (response.status === 401) throw new Error(t.auth);
            const data = await response.json();
            if (!response.ok || data.error) throw new Error(data.error || t.requestError);
            return data;
        } catch (error) {
            if (timedOut) throw new Error(t.timeout);
            if (error instanceof SyntaxError || error instanceof TypeError) throw new Error(t.requestError);
            throw error;
        } finally {
            clearTimeout(timer);
            pass.signal.removeEventListener('abort', cancel);
        }
    }

    function placement(server, project) {
        const link = document.createElement('a');
        const active = project.components.filter(row => row.status === 'active').length;
        link.className = 'badge text-decoration-none me-1 mb-1 ' + (window.PROJECT_STATE_CLASSES[project.state] || '');
        link.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(server.id));
        link.textContent = `${server.name || server.ip_address} · ${active}/${project.components.length}`;
        link.title = `${t[project.state] || t.unknown}\n` + project.components.map(row =>
            `${row.name}${t[row.kind] ? ' (' + t[row.kind] + ')' : ''}: ${t[row.status] || t.unknown}`).join('\n');
        return link;
    }

    function render() {
        const done = servers.filter(server => server.projects || server.error);
        const placements = new Map(config.projects.map(name => [name, []]));
        done.forEach(server => (server.projects || []).forEach(project => {
            if (project.state !== 'unknown' && placements.has(project.name)) placements.get(project.name).push([server, project]);
        }));
        body.replaceChildren();
        const missing = [];
        placements.forEach((found, name) => {
            if (!found.length) { missing.push(name); return; }
            const row = document.createElement('tr');
            const title = document.createElement('th');
            title.scope = 'row';
            title.textContent = name;
            const cell = document.createElement('td');
            found.forEach(([server, project]) => cell.append(placement(server, project)));
            row.append(title, cell);
            body.append(row);
        });
        const finished = done.length === servers.length && servers.length > 0;
        if (!body.children.length && finished) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 2;
            cell.className = 'text-body-secondary';
            cell.textContent = t.notFound;
            row.append(cell);
            body.append(row);
        }
        absent.textContent = finished && missing.length && body.querySelector('th')
            ? t.absent.replace('{names}', missing.join(', ')) : '';
        const failed = servers.filter(server => server.error || (server.projects || []).some(p => p.state === 'unknown'));
        errors.textContent = failed.length
            ? t.errors.replace('{names}', failed.map(server => (server.name || server.ip_address)
                + (server.error ? ` (${server.error})` : '')).join('; ')) : '';
        if (servers.length) {
            progress.textContent = t.progress.replace('{done}', done.length).replace('{total}', servers.length);
            if (completedAt) progress.textContent += ' · ' + t.completed.replace('{time}', completedAt.toLocaleTimeString(locale));
            else progress.textContent += ' · ' + t.checking;
        }
    }

    async function start() {
        if (run) return;
        if (!config.projects.length) { progress.textContent = t.noProjects; return; }
        const pass = new AbortController();
        run = pass;
        refresh.disabled = true;
        servers = [];
        completedAt = null;
        body.replaceChildren();
        absent.textContent = errors.textContent = '';
        progress.textContent = t.loading;
        body.setAttribute('aria-busy', 'true');
        try {
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            servers = inventory.servers;
            if (!servers.length) { progress.textContent = t.empty; return; }
            render();
            let next = 0;
            async function worker() {
                while (run === pass && next < servers.length) {
                    const server = servers[next++];
                    try {
                        const data = await getJSON(config.snapshotUrl.replace('__SERVER__', encodeURIComponent(server.id)), pass);
                        if (run !== pass) return;
                        server.projects = data.stats;
                    } catch (error) {
                        if (run !== pass) return;
                        server.error = error.message;
                    }
                    render();
                }
            }
            await Promise.all(Array.from({length: Math.min(4, servers.length)}, worker));
            if (run === pass) { completedAt = new Date(); render(); }
        } catch (error) {
            if (run === pass) progress.textContent = error.message;
        } finally {
            if (run === pass) {
                run = null;
                refresh.disabled = false;
                body.setAttribute('aria-busy', 'false');
            }
        }
    }

    modal.addEventListener('shown.bs.modal', start);
    modal.addEventListener('hide.bs.modal', () => {
        if (run) { const pass = run; run = null; pass.abort(); }
        refresh.disabled = false;
        body.setAttribute('aria-busy', 'false');
    });
    refresh.addEventListener('click', start);
})();
