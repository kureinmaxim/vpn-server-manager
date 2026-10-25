(function () {
    const modal = document.getElementById('botsCheckModal');
    const config = window.BOTS_CHECK_CONFIG;
    if (!modal || !config) return;
    const t = config.i18n;
    const nodesBox = document.getElementById('bots-check-nodes');
    const errorsBox = document.getElementById('bots-check-errors');
    const sendersBox = document.getElementById('bots-check-senders');
    const processBox = document.getElementById('bots-check-process');
    const extraBox = document.getElementById('bots-check-extra');
    const progress = document.getElementById('bots-check-progress');
    const meshLine = document.getElementById('bots-check-mesh');
    const refresh = document.getElementById('bots-check-refresh');
    const locale = document.documentElement.lang || undefined;
    const STATE_CLASSES = {running: 'text-bg-success', partial: 'text-bg-warning', restarting: 'text-bg-warning',
        failed: 'text-bg-danger', stopped: 'text-bg-secondary', idle: 'bg-body-tertiary text-body border', unknown: 'text-bg-secondary'};
    const STATE_FROM_DOCKER = {running: 'running', restarting: 'restarting', exited: 'stopped', created: 'stopped', paused: 'stopped', dead: 'failed'};
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

    // «12 д 4 ч» is read faster than a date; the exact time stays in the tooltip.
    function age(iso) {
        const date = iso ? new Date(iso) : null;
        if (!date || isNaN(date)) return '';
        const minutes = Math.max(0, Math.round((Date.now() - date) / 60000));
        const days = Math.floor(minutes / 1440), hours = Math.floor(minutes % 1440 / 60);
        if (days) return t.days.replace('{count}', days) + (hours && days < 10 ? ' ' + t.hours.replace('{count}', hours) : '');
        if (hours) return t.hours.replace('{count}', hours);
        return t.minutes.replace('{count}', minutes % 60);
    }

    function bytes(value) {
        if (typeof value !== 'number' || !value) return '';
        const units = ['B', 'KiB', 'MiB', 'GiB'];
        let size = value, unit = 0;
        while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit++; }
        return `${size.toFixed(unit > 1 ? 1 : 0)} ${units[unit]}`;
    }

    function badge(state, text) {
        return el('span', 'badge ' + (STATE_CLASSES[state] || STATE_CLASSES.unknown), text || t[state] || t.unknown);
    }

    function nodeName(entry) {
        return entry.server.name || entry.server.ip_address;
    }

    function table(headers, className = '') {
        const wrap = el('div', 'table-responsive');
        const tableNode = el('table', 'table table-sm align-middle mb-0 bots-check-table ' + className);
        const head = el('tr');
        headers.forEach(label => {
            const th = el('th', '', label);
            th.scope = 'col';
            head.append(th);
        });
        const thead = el('thead');
        thead.append(head);
        const tbody = el('tbody');
        tableNode.append(thead, tbody);
        wrap.append(tableNode);
        return {wrap, tbody};
    }

    function cell(content, className) {
        const td = el('td', className);
        if (content instanceof Node) td.append(content); else if (content !== undefined) td.textContent = content;
        return td;
    }

    function timeCell(iso, className) {
        const td = cell(age(iso), className);
        if (iso) td.title = when(iso);
        return td;
    }

    function notes(stats) {
        const node = stats.node || {};
        const list = [];
        if (node.os === 'macos') list.push(t.macos);
        else if (!node.systemd) list.push(t.noSystemd);
        if ((node.docker === 'unavailable' && node.os !== 'macos') || (node.tos && node.docker !== 'ok')) list.push(node.tos ? t.dockerTos : t.dockerUnavailable);
        (node.kuma || []).forEach(item => { if (t.kumaStates[item.state]) list.push(t.kumaStates[item.state]); });
        const stacks = node.stacks || {};
        if (stacks.files && !(stats.senders || []).some(row => row.kind === 'stack')) list.push(t.stacksClean.replace('{count}', stacks.files));
        if (stacks.unreadable && stacks.unreadable.length) list.push(t.stacksClosed.replace('{names}', stacks.unreadable.join(', ')));
        return list;
    }

    // ---- Nodes: one row of chips instead of a box per node -------------------------------------------------

    function renderNodes() {
        nodesBox.replaceChildren();
        errorsBox.replaceChildren();
        nodes.forEach(entry => {
            const chip = el(entry.local ? 'span' : 'a', 'bots-check-chip badge rounded-pill border text-decoration-none d-inline-flex align-items-center gap-1');
            if (!entry.local) chip.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(entry.server.id));
            let icon;
            if (entry.error) {
                icon = el('i', 'bi bi-exclamation-triangle-fill text-warning');
                chip.classList.add('bots-check-chip-error');
            } else if (entry.stats) {
                const count = entry.stats.bots.length + senderCount(entry);
                icon = el('i', count ? 'bi bi-check-circle-fill text-success' : 'bi bi-dash-circle text-body-secondary');
            } else {
                icon = el('span', 'spinner-border spinner-border-sm');
            }
            icon.setAttribute('aria-hidden', 'true');
            chip.append(icon, el('span', '', nodeName(entry)), el('span', 'text-body-secondary', t.kinds[entry.server.kind] || 'VPS'));
            const tips = [entry.server.ip_address, ...(entry.stats ? notes(entry.stats) : []), entry.error].filter(Boolean);
            chip.title = tips.join('\n');
            nodesBox.append(chip);
            if (entry.error) errorsBox.append(el('div', '', `${nodeName(entry)}: ${entry.error}`));
        });
    }

    function senderCount(entry) {
        return ((entry.stats && entry.stats.senders) || []).length;
    }

    // ---- Sending-only bots: first, one card per bot ID, places in aligned columns ---------------------------

    function schedule(items) {
        return (items || []).map(item => {
            const [key, value] = [item.slice(0, item.indexOf('=')), item.slice(item.indexOf('=') + 1)];
            if (key === 'OnUnitActiveUSec' || key === 'OnUnitInactiveUSec') return t.every.replace('{value}', value);
            if (key === 'OnBootUSec' || key === 'OnStartupUSec') return t.afterBoot.replace('{value}', value);
            return value;
        }).join(', ');
    }

    function runBadge(row) {
        const states = {ok: ['running', t.runOk], never: ['stopped', t.neverRun],
            running: ['restarting', t.runNow], failed: ['failed', t.runFailed.replace('{code}', row.exit_status ?? '?')]};
        const [state, text] = states[row.result] || states.never;
        return badge(state, text);
    }

    function senderGroups() {
        // One bot ID across nodes and places is one bot; rows without an ID stay separate.
        const groups = new Map();
        nodes.forEach(entry => ((entry.stats && entry.stats.senders) || []).forEach(row => {
            (row.bots.length ? row.bots : [null]).forEach(bot => {
                const key = bot ? 'id:' + bot.id : `none:${entry.server.id}:${row.kind}:${row.name}`;
                if (!groups.has(key)) groups.set(key, {bot, places: []});
                const group = groups.get(key);
                if (bot && bot.username && !group.bot.username) group.bot = bot;
                group.places.push({node: nodeName(entry), row});
            });
        }));
        return [...groups.values()];
    }

    function placeRow(place) {
        const row = place.row;
        const tr = el('tr');
        let where, when_, last, result;
        if (row.kind === 'timer') {
            where = `${row.name.replace(/\.service$/, '')} · ${t.timer}`;
            when_ = cell(schedule(row.schedule) + (row.next ? ` · ${t.nextRun.replace('{time}', when(row.next))}` : ''), 'text-body-secondary');
            last = timeCell(row.last_run, 'text-nowrap text-body-secondary');
            result = runBadge(row);
        } else if (row.kind === 'kuma') {
            where = `Uptime Kuma «${row.name}»`;
            when_ = cell(t.kumaWhen, 'text-body-secondary');
            last = cell('');
            result = badge(row.active ? 'running' : 'stopped', row.active ? t.kumaOn : t.kumaOff);
        } else {
            const kind = row.kind === 'stack' ? t.stack : `${t.container}, ${t[STATE_FROM_DOCKER[row.state]] || row.state}`;
            where = `${row.name} · ${kind}`;
            when_ = cell(t.variables.replace('{names}', row.variables.join(', ')), 'text-body-secondary');
            last = cell('');
            result = el('span');
        }
        tr.append(cell(place.node, 'text-nowrap'), cell(where, 'bots-check-component'), when_, last, cell(result, 'text-end'));
        return tr;
    }

    function renderSenders() {
        const groups = senderGroups();
        sendersBox.replaceChildren();
        if (!groups.length) {
            sendersBox.append(el('div', 'small text-body-secondary', allDone() ? t.sendersNone : t.sendersWait));
            return;
        }
        groups.forEach(group => {
            const box = el('div', 'bots-check-card border rounded mb-2');
            const head = el('div', 'd-flex flex-wrap align-items-baseline gap-2 px-2 pt-2 pb-1');
            head.append(el('i', 'bi bi-send-fill text-info'));
            if (group.bot) {
                head.append(el('span', 'fw-semibold fs-6', group.bot.username ? '@' + group.bot.username : t.botId.replace('{id}', group.bot.id)));
                if (group.bot.username) head.append(el('small', 'text-body-secondary font-monospace', t.botId.replace('{id}', group.bot.id)));
            } else {
                const row = group.places[0].row;
                head.append(el('span', 'fw-semibold', t.unidentified));
                if (row.kind === 'timer') head.append(el('small', 'text-body-secondary', row.token_source === 'kuma' ? t.tokenInKuma : t.tokenNotFound));
            }
            const {wrap, tbody} = table([t.node, t.where, t.scheduleCol, t.lastRunCol, '']);
            group.places.forEach(place => tbody.append(placeRow(place)));
            box.append(head, wrap);
            sendersBox.append(box);
        });
    }

    // ---- Bots with a process: one table across all nodes ----------------------------------------------------

    function componentText(row) {
        const parts = [`${row.name} (${t[row.kind] || row.kind}${row.count > 1 ? ' ×' + row.count : ''})`];
        if (row.state !== 'running') parts.push(t[row.state] || t.unknown);
        if (row.users && row.users.length) parts.push(t.user.replace('{name}', row.users.join(', ')));
        if (row.launchd) parts.push(row.labels && row.labels.length ? 'launchd ' + row.labels.join(', ') : t.launchdAgent);
        if (row.since) parts.push((row.oneshot && row.state !== 'running' ? t.lastRun : t.since).replace('{time}', when(row.since)));
        if (row.result && row.oneshot) parts.push(row.result);
        if (row.result && row.kind === 'container') parts.push('health: ' + row.result);
        if (row.restarts) parts.push(t.restarts.replace('{count}', row.restarts));
        if (row.memory_bytes) parts.push(t.memory.replace('{value}', bytes(row.memory_bytes)));
        return parts.join(' · ');
    }

    function componentsCell(bot) {
        const td = el('td', 'small text-body-secondary bots-check-component');
        const rows = bot.components;
        const short = rows.length === 1 ? rows[0].name : `${rows.length} × ${t[rows[0].kind] || rows[0].kind}`;
        const extra = [];
        if (rows[0].users && rows[0].users.length) extra.push(rows[0].users.join(', '));
        if (rows.some(row => row.launchd)) extra.push('launchd');
        if (rows.some(row => row.restarts)) extra.push(t.restarts.replace('{count}', rows.reduce((sum, row) => sum + (row.restarts || 0), 0)));
        const details = el('details');
        details.append(el('summary', '', [short, ...extra].join(' · ')));
        rows.forEach(row => details.append(el('div', 'ps-3', componentText(row))));
        td.append(details);
        (bot.tasks || []).forEach(task => {
            const line = el('div', 'ps-3');
            line.textContent = `↳ ${task.name} · ${task.state === 'running' ? t.since.replace('{time}', when(task.since)) : task.state === 'idle' ? t.taskIdle : t.unknown}`;
            td.append(line);
        });
        return td;
    }

    function processRows() {
        const rows = [];
        nodes.forEach(entry => ((entry.stats && entry.stats.bots) || []).forEach(bot => rows.push({entry, bot})));
        // The same bot on several nodes stays together.
        return rows.sort((a, b) => a.bot.name.localeCompare(b.bot.name, locale));
    }

    function renderProcess() {
        processBox.replaceChildren();
        const rows = processRows();
        if (!rows.length) {
            processBox.append(el('div', 'small text-body-secondary', allDone() ? t.processNone : t.sendersWait));
            return;
        }
        const {wrap, tbody} = table([t.bot, t.node, t.state, t.uptime, t.memoryCol, t.components]);
        rows.forEach(({entry, bot}) => {
            const tr = el('tr');
            const name = el('th', 'fw-semibold text-nowrap', bot.name);
            name.scope = 'row';
            const state = el('td', 'text-nowrap');
            state.append(badge(bot.state));
            if (bot.health) {
                const health = badge(bot.health === 'ok' ? 'running' : 'failed', bot.health === 'ok' ? 'health ✓' : 'health ✗');
                health.classList.add('ms-1');
                health.title = bot.health === 'ok' ? t.healthOk : t.healthFail;
                state.append(health);
            }
            const alive = bot.components.filter(row => row.since && !row.oneshot).map(row => row.since).sort();
            const memory = bot.components.reduce((sum, row) => sum + (row.memory_bytes || 0), 0);
            tr.append(name, cell(nodeName(entry), 'text-nowrap'), state, timeCell(alive[0], 'text-nowrap'),
                cell(bytes(memory), 'text-nowrap text-body-secondary'), componentsCell(bot));
            tbody.append(tr);
        });
        const box = el('div', 'bots-check-card border rounded pt-1');
        box.append(wrap);
        processBox.append(box);
    }

    // ---- Secondary: folded at the bottom --------------------------------------------------------------------

    function fold(title, lines) {
        const details = el('details', 'mb-1');
        details.append(el('summary', 'text-body-secondary', title));
        lines.forEach(line => details.append(el('div', 'ps-3 text-body-secondary bots-check-component', line)));
        return details;
    }

    function renderExtra() {
        extraBox.replaceChildren();
        const done = nodes.filter(entry => entry.stats);
        const empty = done.filter(entry => !entry.stats.bots.length && !senderCount(entry)).map(nodeName);
        if (empty.length) extraBox.append(el('div', 'text-body-secondary mb-1', t.withoutBots.replace('{names}', empty.join(', '))));
        const helpers = [];
        done.forEach(entry => {
            // A helper timer that turned out to be a sending bot is shown once, among the senders.
            const sending = new Set(senderCountRows(entry).map(row => row.name));
            entry.stats.helpers.filter(row => !sending.has(row.name))
                .forEach(row => helpers.push(`${nodeName(entry)} · ${row.owner}: ${componentText(row)}`));
        });
        if (helpers.length) extraBox.append(fold(t.helpersAll.replace('{count}', helpers.length), helpers));
        const suspects = [];
        done.forEach(entry => entry.stats.suspects.forEach(item => {
            const where = [t[item.kind] || item.kind, item.script, item.user].filter(Boolean).join(', ');
            suspects.push(`${nodeName(entry)} · ${item.name} (${where})`);
        }));
        if (suspects.length) extraBox.append(fold(t.suspectsAll.replace('{count}', suspects.length), suspects));
        const notesLines = [];
        done.forEach(entry => notes(entry.stats).forEach(text => notesLines.push(`${nodeName(entry)} · ${text}`)));
        if (notesLines.length) extraBox.append(fold(t.notesAll.replace('{count}', notesLines.length), notesLines));
    }

    function senderCountRows(entry) {
        return ((entry.stats && entry.stats.senders) || []).filter(row => row.kind === 'timer');
    }

    function allDone() {
        return nodes.length && nodes.every(entry => entry.stats || entry.error);
    }

    function renderAll() {
        renderNodes();
        renderSenders();
        renderProcess();
        renderExtra();
        const done = nodes.filter(entry => entry.stats || entry.error).length;
        progress.textContent = t.progress.replace('{done}', done).replace('{total}', nodes.length) + ' · '
            + (completedAt ? t.completed.replace('{time}', completedAt.toLocaleTimeString(locale)) : t.checking);
    }

    async function loadMesh(pass) {
        try {
            const data = await getJSON(config.meshUrl, pass, 10000);
            if (run !== pass) return;
            // This computer is checked locally when possible, so it is not "without a card".
            const names = (data.nodes || []).filter(node => !(node.self && config.localUrl))
                .map(node => node.name + (node.self ? ` (${t.thisPc})` : node.online ? '' : ` (${t.offline})`));
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
        [nodesBox, errorsBox, sendersBox, processBox, extraBox].forEach(box => box.replaceChildren());
        meshLine.textContent = '';
        progress.textContent = t.loading;
        nodesBox.setAttribute('aria-busy', 'true');
        const mesh = loadMesh(pass);
        try {
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            nodes = inventory.servers.map(server => ({server}));
            if (config.localUrl) nodes.push({server: {id: 'local', name: t.thisComputer, kind: 'pc', ip_address: ''}, local: true});
            if (!nodes.length) { progress.textContent = t.empty; return; }
            renderAll();
            let next = 0;
            async function worker() {
                while (run === pass && next < nodes.length) {
                    const entry = nodes[next++];
                    try {
                        const url = entry.local ? config.localUrl : config.snapshotUrl.replace('__SERVER__', encodeURIComponent(entry.server.id));
                        const data = await getJSON(url, pass, 50000);
                        if (run !== pass) return;
                        entry.stats = data.stats;
                        if (entry.local && data.name) entry.server.name = `${t.thisComputer} (${data.name})`;
                    } catch (error) {
                        if (run !== pass) return;
                        entry.error = error.message;
                    }
                    renderAll();
                }
            }
            await Promise.all(Array.from({length: Math.min(6, nodes.length)}, worker));
            await mesh;
            if (run === pass) { completedAt = new Date(); renderAll(); }
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
