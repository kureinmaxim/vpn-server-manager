(function () {
    const modal = document.getElementById('botsCheckModal');
    const config = window.BOTS_CHECK_CONFIG;
    if (!modal || !config) return;
    const t = config.i18n;
    const nodesBox = document.getElementById('bots-check-nodes');
    const progress = document.getElementById('bots-check-progress');
    const meshLine = document.getElementById('bots-check-mesh');
    const refresh = document.getElementById('bots-check-refresh');
    const sendersBox = document.getElementById('bots-check-senders');
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
        if (row.users && row.users.length) parts.push(t.user.replace('{name}', row.users.join(', ')));
        if (row.launchd) parts.push(row.labels && row.labels.length ? 'launchd ' + row.labels.join(', ') : t.launchdAgent);
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
        (bot.tasks || []).forEach(row => {
            const text = row.state === 'running' ? componentText(row)
                : `${row.name} (${t.task}) · ${row.state === 'idle' ? t.taskIdle : t.unknown}`;
            details.append(el('div', 'bots-check-component ps-3', '↳ ' + text));
        });
        tr.append(name, state, details);
        return tr;
    }

    function notes(stats) {
        const node = stats.node || {};
        const list = [];
        if (node.os === 'macos') list.push(t.macos);
        else if (!node.systemd) list.push(t.noSystemd);
        const stacks = node.stacks || {};
        if (stacks.files && !(stats.senders || []).some(row => row.kind === 'stack')) list.push(t.stacksClean.replace('{count}', stacks.files));
        if (stacks.unreadable && stacks.unreadable.length) list.push(t.stacksClosed.replace('{names}', stacks.unreadable.join(', ')));
        if ((node.docker === 'unavailable' && node.os !== 'macos') || (node.tos && node.docker !== 'ok')) list.push(node.tos ? t.dockerTos : t.dockerUnavailable);
        (node.kuma || []).forEach(item => { if (t.kumaStates[item.state]) list.push(t.kumaStates[item.state]); });
        return list;
    }

    function schedule(items) {
        return (items || []).map(item => {
            const [key, value] = [item.slice(0, item.indexOf('=')), item.slice(item.indexOf('=') + 1)];
            if (key === 'OnUnitActiveUSec' || key === 'OnUnitInactiveUSec') return t.every.replace('{value}', value);
            if (key === 'OnBootUSec' || key === 'OnStartupUSec') return t.afterBoot.replace('{value}', value);
            return value;
        }).join(', ');
    }

    function runBadge(row) {
        const states = {ok: ['text-bg-success', t.runOk], never: ['text-bg-secondary', t.neverRun],
            running: ['text-bg-warning', t.runNow], failed: ['text-bg-danger', t.runFailed.replace('{code}', row.exit_status ?? '?')]};
        const [className, text] = states[row.result] || states.never;
        return el('span', 'badge ' + className, text);
    }

    function placeLine(place) {
        const row = place.row;
        const line = el('div', 'd-flex align-items-baseline gap-2 small mt-1');
        const parts = [place.node];
        if (row.kind === 'timer') {
            parts.push(`${row.name} (${t.timer})`);
            if (row.schedule.length) parts.push(schedule(row.schedule));
            if (row.next) parts.push(t.nextRun.replace('{time}', when(row.next)));
            if (row.last_run) parts.push(t.lastRun.replace('{time}', when(row.last_run)));
            line.append(runBadge(row));
        } else if (row.kind === 'kuma') {
            parts.push(`Uptime Kuma «${row.name}» (${row.container})`);
            line.append(el('span', 'badge ' + (row.active ? 'text-bg-success' : 'text-bg-secondary'), row.active ? t.kumaOn : t.kumaOff));
        } else if (row.kind === 'stack') {
            parts.push(`${row.name} (${t.stack})`);
            parts.push(t.variables.replace('{names}', row.variables.join(', ')));
        } else {
            parts.push(`${row.name} (${t.container}, ${t[STATE_FROM_DOCKER[row.state]] || row.state})`);
            parts.push(t.variables.replace('{names}', row.variables.join(', ')));
        }
        line.append(el('span', 'text-body-secondary bots-check-component flex-grow-1', parts.join(' · ')));
        line.firstChild.classList.add('flex-shrink-0');
        return line;
    }

    const STATE_FROM_DOCKER = {running: 'running', restarting: 'restarting', exited: 'stopped', created: 'stopped', paused: 'stopped', dead: 'failed'};

    function senderGroups() {
        // One bot ID across nodes and places is one bot; rows without an ID stay separate.
        const groups = new Map();
        nodes.forEach(entry => ((entry.stats && entry.stats.senders) || []).forEach(row => {
            const node = entry.server.name || entry.server.ip_address;
            (row.bots.length ? row.bots : [null]).forEach(bot => {
                const key = bot ? 'id:' + bot.id : `none:${entry.server.id}:${row.kind}:${row.name}`;
                if (!groups.has(key)) groups.set(key, {bot, places: []});
                const group = groups.get(key);
                if (bot && bot.username && !group.bot.username) group.bot = bot;
                group.places.push({node, row});
            });
        }));
        return [...groups.values()];
    }

    function renderSenders() {
        const groups = senderGroups();
        sendersBox.replaceChildren();
        if (!groups.length) {
            const done = nodes.length && nodes.every(entry => entry.stats || entry.error);
            sendersBox.append(el('div', 'small text-body-secondary', done ? t.sendersNone : t.sendersWait));
            return;
        }
        groups.forEach(group => {
            const box = el('div', 'bots-check-node border rounded p-2 mb-2');
            const head = el('div', 'd-flex flex-wrap align-items-baseline gap-2');
            if (group.bot) {
                head.append(el('span', 'fw-semibold', group.bot.username ? '@' + group.bot.username : t.botId.replace('{id}', group.bot.id)));
                if (group.bot.username) head.append(el('small', 'text-body-secondary', t.botId.replace('{id}', group.bot.id)));
            } else {
                const row = group.places[0].row;
                head.append(el('span', 'fw-semibold', t.unidentified));
                if (row.kind === 'timer') head.append(el('small', 'text-body-secondary', row.token_source === 'kuma' ? t.tokenInKuma : t.tokenNotFound));
            }
            box.append(head);
            group.places.forEach(place => box.append(placeLine(place)));
            sendersBox.append(box);
        });
    }

    function renderNode(entry) {
        const box = entry.box;
        box.replaceChildren();
        const head = el('div', 'd-flex flex-wrap align-items-center gap-2 mb-2');
        const title = el(entry.local ? 'span' : 'a', 'fw-semibold text-decoration-none', entry.server.name || entry.server.ip_address);
        if (!entry.local) title.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(entry.server.id));
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
        const senders = stats.senders || [];
        if (senders.length) box.append(el('div', 'small text-info-emphasis mt-1', t.sendersOnNode.replace('{count}', senders.length)));
        // A helper timer that turned out to be a sending bot is shown once, in the senders section.
        const sending = new Set(senders.filter(row => row.kind === 'timer').map(row => row.name));
        const helpers = stats.helpers.filter(row => !sending.has(row.name));
        if (helpers.length) {
            const details = el('details', 'small mt-1');
            details.append(el('summary', 'text-body-secondary', t.helpers.replace('{count}', helpers.length)));
            helpers.forEach(row => {
                const line = el('div', 'd-flex flex-wrap align-items-center gap-2 mt-1');
                line.append(badge(row.state), el('span', 'text-body-secondary', `${row.owner}: ${componentText(row)}`));
                details.append(line);
            });
            box.append(details);
        }
        if (stats.suspects.length) {
            box.append(el('div', 'small text-info-emphasis mt-1',
                t.suspects.replace('{names}', stats.suspects.map(item => {
                    const where = [t[item.kind] || item.kind, item.script, item.user].filter(Boolean).join(', ');
                    return `${item.name} (${where})`;
                }).join('; '))));
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
        nodesBox.replaceChildren();
        sendersBox.replaceChildren();
        meshLine.textContent = '';
        progress.textContent = t.loading;
        nodesBox.setAttribute('aria-busy', 'true');
        const mesh = loadMesh(pass);
        try {
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            const servers = inventory.servers.map(server => ({server}));
            if (config.localUrl) servers.push({server: {id: 'local', name: t.thisComputer, kind: 'pc', ip_address: ''}, local: true});
            if (!servers.length) { progress.textContent = t.empty; return; }
            nodes = servers.map(item => {
                const box = el('section', 'bots-check-node border rounded p-2 mb-2');
                nodesBox.append(box);
                const entry = {...item, box};
                renderNode(entry);
                return entry;
            });
            renderProgress();
            renderSenders();
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
                    renderNode(entry);
                    renderProgress();
                    renderSenders();
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
