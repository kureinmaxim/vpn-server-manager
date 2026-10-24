(function () {
    const modal = document.getElementById('botsCheckModal');
    const config = window.BOTS_CHECK_CONFIG;
    if (!modal || !config) return;
    const t = config.i18n;
    const nodesBox = document.getElementById('bots-check-nodes');
    const progress = document.getElementById('bots-check-progress');
    const meshLine = document.getElementById('bots-check-mesh');
    const refresh = document.getElementById('bots-check-refresh');
    const locale = document.documentElement.lang || undefined;
    const STATE_CLASSES = {running: 'text-bg-success', partial: 'text-bg-warning', restarting: 'text-bg-warning',
        failed: 'text-bg-danger', stopped: 'text-bg-secondary', idle: 'bg-body-tertiary text-body border', unknown: 'text-bg-secondary'};
    let run = null;
    let nodes = [];
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

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function when(iso) {
        const date = iso ? new Date(iso) : null;
        return date && !isNaN(date) ? date.toLocaleString(locale, {dateStyle: 'short', timeStyle: 'short'}) : '';
    }

    function bytes(value) {
        if (typeof value !== 'number') return '';
        const units = ['B', 'KiB', 'MiB', 'GiB'];
        let size = value, unit = 0;
        while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit++; }
        return `${size.toFixed(unit > 1 ? 1 : 0)} ${units[unit]}`;
    }

    function badge(state) {
        return el('span', 'badge ' + (STATE_CLASSES[state] || STATE_CLASSES.unknown), t[state] || t.unknown);
    }

    function componentText(row) {
        const parts = [`${row.name} (${t[row.kind] || row.kind}${row.count > 1 ? ' ×' + row.count : ''})`];
        if (row.state !== 'running') parts.push(t[row.state] || t.unknown);
        if (row.since) parts.push((row.oneshot && row.state !== 'running' ? t.lastRun : t.since).replace('{time}', when(row.since)));
        if (row.result && row.oneshot) parts.push(row.result);
        if (row.result && row.kind === 'container') parts.push('health: ' + row.result);
        if (row.restarts) parts.push(t.restarts.replace('{count}', row.restarts));
        if (row.memory_bytes) parts.push(t.memory.replace('{value}', bytes(row.memory_bytes)));
        return parts.join(' · ');
    }

    function botRow(bot) {
        const tr = el('tr');
        const name = el('th', 'fw-semibold', bot.name);
        name.scope = 'row';
        const state = el('td');
        state.append(badge(bot.state));
        if (bot.health) {
            const health = el('span', 'badge ms-1 ' + (bot.health === 'ok' ? 'text-bg-success' : 'text-bg-danger'),
                bot.health === 'ok' ? 'health ✓' : 'health ✗');
            health.title = bot.health === 'ok' ? t.healthOk : t.healthFail;
            state.append(health);
        }
        const details = el('td', 'small text-body-secondary');
        bot.components.forEach(row => details.append(el('div', 'bots-check-component', componentText(row))));
        tr.append(name, state, details);
        return tr;
    }

    function notes(stats) {
        const node = stats.node || {};
        const list = [];
        if (!node.systemd) list.push(t.noSystemd);
        if (node.docker === 'unavailable' || (node.tos && node.docker !== 'ok')) list.push(node.tos ? t.dockerTos : t.dockerUnavailable);
        return list;
    }

    function renderNode(entry) {
        const box = entry.box;
        box.replaceChildren();
        const head = el('div', 'd-flex flex-wrap align-items-center gap-2 mb-2');
        const title = el('a', 'fw-semibold text-decoration-none', entry.server.name || entry.server.ip_address);
        title.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(entry.server.id));
        head.append(title, el('span', 'badge rounded-pill bg-body-tertiary text-body border', t.kinds[entry.server.kind] || 'VPS'));
        if (entry.server.ip_address) head.append(el('small', 'text-body-secondary', entry.server.ip_address));
        box.append(head);
        if (!entry.stats && !entry.error) {
            const wait = el('div', 'small text-body-secondary d-flex align-items-center gap-2');
            wait.append(el('span', 'spinner-border spinner-border-sm'), el('span', '', t.checking));
            wait.querySelector('.spinner-border').setAttribute('aria-hidden', 'true');
            box.append(wait);
            return;
        }
        if (entry.error) {
            box.append(el('div', 'small text-warning-emphasis', entry.error));
            return;
        }
        const stats = entry.stats;
        const extra = notes(stats);
        if (stats.bots.length) {
            const wrap = el('div', 'table-responsive');
            const table = el('table', 'table table-sm align-middle mb-1 bots-check-table');
            const thead = el('thead');
            const headRow = el('tr');
            [t.bot, t.state, t.details].forEach(label => {
                const th = el('th', '', label);
                th.scope = 'col';
                headRow.append(th);
            });
            thead.append(headRow);
            const tbody = el('tbody');
            stats.bots.forEach(bot => tbody.append(botRow(bot)));
            table.append(thead, tbody);
            wrap.append(table);
            box.append(wrap);
        } else {
            box.append(el('div', 'small text-body-secondary', t.noBots));
        }
        if (stats.helpers.length) {
            const details = el('details', 'small mt-1');
            details.append(el('summary', 'text-body-secondary', t.helpers.replace('{count}', stats.helpers.length)));
            stats.helpers.forEach(row => {
                const line = el('div', 'd-flex flex-wrap align-items-center gap-2 mt-1');
                line.append(badge(row.state), el('span', 'text-body-secondary', `${row.owner}: ${componentText(row)}`));
                details.append(line);
            });
            box.append(details);
        }
        if (stats.suspects.length) {
            box.append(el('div', 'small text-info-emphasis mt-1',
                t.suspects.replace('{names}', stats.suspects.map(item => `${item.name} (${t[item.kind] || item.kind})`).join(', '))));
        }
        extra.forEach(text => box.append(el('div', 'small text-body-secondary mt-1', text)));
    }

    function renderProgress() {
        const done = nodes.filter(entry => entry.stats || entry.error).length;
        progress.textContent = t.progress.replace('{done}', done).replace('{total}', nodes.length) + ' · '
            + (completedAt ? t.completed.replace('{time}', completedAt.toLocaleTimeString(locale)) : t.checking);
    }

    async function loadMesh(pass) {
        try {
            const data = await getJSON(config.meshUrl, pass, 10000);
            if (run !== pass) return;
            const names = (data.nodes || []).map(node => node.name + (node.self ? ` (${t.thisPc})` : node.online ? '' : ` (${t.offline})`));
            meshLine.textContent = names.length ? t.meshOnly.replace('{names}', names.join(', ')) : '';
        } catch (error) {
            if (run === pass) meshLine.textContent = '';
        }
    }

    async function start() {
        if (run) return;
        const pass = new AbortController();
        run = pass;
        refresh.disabled = true;
        nodes = [];
        completedAt = null;
        nodesBox.replaceChildren();
        meshLine.textContent = '';
        progress.textContent = t.loading;
        nodesBox.setAttribute('aria-busy', 'true');
        const mesh = loadMesh(pass);
        try {
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            if (!inventory.servers.length) { progress.textContent = t.empty; return; }
            nodes = inventory.servers.map(server => {
                const box = el('section', 'bots-check-node border rounded p-2 mb-2');
                nodesBox.append(box);
                const entry = {server, box};
                renderNode(entry);
                return entry;
            });
            renderProgress();
            let next = 0;
            async function worker() {
                while (run === pass && next < nodes.length) {
                    const entry = nodes[next++];
                    try {
                        const data = await getJSON(config.snapshotUrl.replace('__SERVER__', encodeURIComponent(entry.server.id)), pass);
                        if (run !== pass) return;
                        entry.stats = data.stats;
                    } catch (error) {
                        if (run !== pass) return;
                        entry.error = error.message;
                    }
                    renderNode(entry);
                    renderProgress();
                }
            }
            await Promise.all(Array.from({length: Math.min(6, nodes.length)}, worker));
            await mesh;
            if (run === pass) { completedAt = new Date(); renderProgress(); }
        } catch (error) {
            if (run === pass) progress.textContent = error.message;
        } finally {
            if (run === pass) {
                run = null;
                refresh.disabled = false;
                nodesBox.setAttribute('aria-busy', 'false');
            }
        }
    }

    modal.addEventListener('shown.bs.modal', start);
    modal.addEventListener('hide.bs.modal', () => {
        if (run) { const pass = run; run = null; pass.abort(); }
        refresh.disabled = false;
        nodesBox.setAttribute('aria-busy', 'false');
    });
    refresh.addEventListener('click', start);
})();
