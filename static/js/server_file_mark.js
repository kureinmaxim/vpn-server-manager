(function () {
    const config = window.SERVER_FILE_MARK;
    const board = document.getElementById('server-board');
    if (!config || !board) return;
    const t = config.i18n || {};
    const CACHE_KEY = 'server-rfm-v1';
    const TTL = 180000;
    const hints = (config.hints || []).map(name => name.toLowerCase());

    function cache() {
        try { return JSON.parse(sessionStorage.getItem(CACHE_KEY) || '{}'); } catch (error) { return {}; }
    }

    function saveCache(data) {
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(data)); } catch (error) { /* private mode */ }
    }

    function filesProject(projects) {
        return (projects || []).find(project => {
            if (project.name === config.name || project.key === 'rust_file_manager') return true;
            return (project.components || []).some(row =>
                hints.some(hint => String(row.name || '').toLowerCase().includes(hint)));
        });
    }

    function paint(id, project) {
        const items = board.querySelectorAll('.server-board-item[data-server-id="' + CSS.escape(String(id)) + '"]');
        const show = project && project.state && project.state !== 'unknown';
        const title = show
            ? [t.files, project.name || config.name, t[project.state] || project.state].filter(Boolean).join(' · ')
            : '';
        items.forEach(item => {
            item.querySelectorAll('.server-file-mark').forEach(holder => {
                holder.hidden = !show;
                holder.title = title;
                holder.setAttribute('aria-label', title);
                holder.classList.toggle('is-up', project && project.state === 'running');
                holder.classList.toggle('is-partial', project && project.state === 'partial');
                holder.classList.toggle('is-down', project && project.state === 'stopped');
                if (config.monitoringUrl) {
                    holder.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(id));
                }
            });
        });
    }

    async function getJSON(url) {
        const response = await fetch(url, {cache: 'no-store', headers: {Accept: 'application/json'}});
        if (!response.ok) throw new Error(String(response.status));
        return response.json();
    }

    const stored = cache();
    const now = Date.now();
    Object.keys(stored).forEach(id => {
        if (stored[id] && now - stored[id].at < TTL) paint(id, stored[id].project);
    });

    (async () => {
        let servers = [];
        try {
            const inventory = await getJSON(config.serversUrl);
            servers = inventory.servers || [];
        } catch (error) { return; }
        let next = 0;
        async function worker() {
            while (next < servers.length) {
                const server = servers[next++];
                const fresh = stored[server.id];
                if (fresh && now - fresh.at < TTL) continue;
                try {
                    const data = await getJSON(config.snapshotUrl.replace('__SERVER__', encodeURIComponent(server.id)));
                    const project = filesProject(data.stats) || null;
                    stored[server.id] = {project, at: Date.now()};
                    saveCache(stored);
                    paint(server.id, project);
                } catch (error) { /* SSH miss: leave the card unmarked. */ }
            }
        }
        await Promise.all(Array.from({length: Math.min(3, servers.length)}, worker));
    })();
})();
