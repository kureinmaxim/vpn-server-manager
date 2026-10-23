(function () {
    const config = window.SERVER_FILE_MARK;
    const board = document.getElementById('server-board');
    if (!config || !board) return;
    const t = config.i18n || {};
    const CACHE_KEY = 'server-role-marks-v2';
    const TTL = 180000;
    const filesHints = (config.hints || []).map(name => name.toLowerCase());
    const dnsHints = (config.dnsHints || []).map(name => name.toLowerCase());
    const chatmailHints = (config.chatmailHints || []).map(name => name.toLowerCase());

    function cache() {
        try { return JSON.parse(sessionStorage.getItem(CACHE_KEY) || '{}'); } catch (error) { return {}; }
    }

    function saveCache(data) {
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(data)); } catch (error) { /* private mode */ }
    }

    function matchProject(projects, spec) {
        const keys = spec.keys || [];
        const hints = spec.hints || [];
        return (projects || []).find(project => {
            if (spec.name && project.name === spec.name) return true;
            if (keys.includes(project.key)) return true;
            return (project.components || []).some(row =>
                hints.some(hint => String(row.name || '').toLowerCase().includes(hint)));
        });
    }

    function filesProject(projects) {
        return matchProject(projects, {
            name: config.name,
            keys: ['rust_file_manager'],
            hints: filesHints,
        });
    }

    function dnsProject(projects) {
        return matchProject(projects, {
            name: config.dnsName,
            keys: ['adguard'],
            hints: dnsHints,
        });
    }

    function chatmailProject(projects) {
        return matchProject(projects, {
            name: config.chatmailName,
            keys: ['chatmail_relay', 'chatmail'],
            hints: chatmailHints,
        }) || (projects || []).find(project => {
            const key = String(project.key || '').toLowerCase();
            const name = String(project.name || '').toLowerCase();
            return key.includes('chatmail') || name.includes('chatmail');
        });
    }

    function paintMark(items, selector, project, label, href) {
        const show = project && project.state && project.state !== 'unknown';
        const title = show
            ? [label, project.name, t[project.state] || project.state].filter(Boolean).join(' · ')
            : '';
        items.forEach(item => {
            item.querySelectorAll(selector).forEach(holder => {
                holder.hidden = !show;
                holder.title = title;
                holder.setAttribute('aria-label', title);
                holder.classList.toggle('is-up', project && project.state === 'running');
                holder.classList.toggle('is-partial', project && project.state === 'partial');
                holder.classList.toggle('is-down', project && project.state === 'stopped');
                if (href) holder.href = href;
            });
        });
    }

    function paint(id, marks) {
        const items = board.querySelectorAll('.server-board-item[data-server-id="' + CSS.escape(String(id)) + '"]');
        const filesHref = config.monitoringUrl
            ? config.monitoringUrl.replace('__SERVER__', encodeURIComponent(id))
            : '';
        const dnsHref = config.diagnosticsUrl
            ? config.diagnosticsUrl.replace('__SERVER__', encodeURIComponent(id)) + '?role=adguard'
            : '';
        const chatmailHref = config.diagnosticsUrl
            ? config.diagnosticsUrl.replace('__SERVER__', encodeURIComponent(id)) + '?role=chatmail'
            : '';
        paintMark(items, '.server-file-mark', marks && marks.files, t.files, filesHref);
        paintMark(items, '.server-dns-mark', marks && marks.dns, t.dns, dnsHref);
        paintMark(items, '.server-chatmail-mark', marks && marks.chatmail, t.chatmail, chatmailHref);
    }

    async function getJSON(url) {
        const response = await fetch(url, {cache: 'no-store', headers: {Accept: 'application/json'}});
        if (!response.ok) throw new Error(String(response.status));
        return response.json();
    }

    const stored = cache();
    const now = Date.now();
    Object.keys(stored).forEach(id => {
        if (stored[id] && now - stored[id].at < TTL) paint(id, stored[id]);
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
                    const marks = {
                        files: filesProject(data.stats) || null,
                        dns: dnsProject(data.stats) || null,
                        chatmail: chatmailProject(data.stats) || null,
                    };
                    stored[server.id] = {files: marks.files, dns: marks.dns, chatmail: marks.chatmail, at: Date.now()};
                    saveCache(stored);
                    paint(server.id, marks);
                } catch (error) { /* SSH miss: leave the card unmarked. */ }
            }
        }
        await Promise.all(Array.from({length: Math.min(3, servers.length)}, worker));
    })();
})();
