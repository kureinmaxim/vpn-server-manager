/* One bounded, cancellable pass; metrics are never polled in the background. */
(() => {
    'use strict';
    const config = window.LOAD_CHECK_CONFIG;
    const modal = document.getElementById('loadCheckModal');
    if (!config || !modal) return;
    const t = config.i18n;
    const locale = document.documentElement.lang;
    const percentNumber = new Intl.NumberFormat(locale, {minimumFractionDigits: 1, maximumFractionDigits: 1});
    const loadNumber = new Intl.NumberFormat(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const body = document.getElementById('load-check-rows');
    const progress = document.getElementById('load-check-progress');
    const refresh = document.getElementById('load-check-refresh');
    const filter = document.getElementById('load-check-filter');
    let run = null;
    let rows = [];
    let sort = {key: 'name', direction: 1};

    function element(tag, text, className) {
        const node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        if (className) node.className = className;
        return node;
    }

    function bytes(value) {
        const units = t.byteUnits;
        let index = 0;
        while (value >= 1024 && index < units.length - 1) { value /= 1024; index++; }
        return value.toLocaleString(locale, {maximumFractionDigits: 1}) + ' ' + units[index];
    }

    function metricCell(metric, detail) {
        const cell = element('td');
        if (!metric) {
            cell.textContent = '—';
            cell.title = t.unavailable;
            return cell;
        }
        cell.append(element('strong', percentNumber.format(metric.used_pct) + '%'));
        if (detail) cell.append(element('span', detail, 'load-detail text-nowrap'));
        const meter = element('div', undefined, 'load-check-meter' + (metric.used_pct >= 90 ? ' is-hot' : metric.used_pct >= 75 ? ' is-warm' : ''));
        const fill = element('span');
        fill.style.width = Math.min(100, Math.max(0, metric.used_pct)) + '%';
        meter.setAttribute('aria-hidden', 'true');
        meter.append(fill);
        cell.append(meter);
        return cell;
    }

    function sortValue(row) {
        if (sort.key === 'name') return row.server.name;
        const metric = row.stats && row.stats[sort.key];
        if (!metric) return null;
        if (sort.key === 'load') return metric.per_core;
        if (sort.key === 'network') return metric.rx_bytes_per_second + metric.tx_bytes_per_second;
        return metric.used_pct;
    }

    function render() {
        body.replaceChildren();
        const query = filter.value.trim().toLocaleLowerCase();
        const visible = rows.filter(row => (row.server.name + ' ' + row.server.ip_address).toLocaleLowerCase().includes(query));
        visible.sort((a, b) => {
            const av = sortValue(a), bv = sortValue(b);
            if (av === null || bv === null) return av === bv ? 0 : av === null ? 1 : -1;
            return sort.direction * (typeof av === 'string' ? av.localeCompare(bv, locale) : av - bv);
        });
        if (!visible.length) {
            const cell = element('td', rows.length ? t.noMatches : t.empty, 'text-center text-body-secondary py-5');
            cell.colSpan = 8;
            const tr = element('tr'); tr.append(cell); body.append(tr);
        }
        for (const row of visible) {
            const tr = element('tr');
            const server = element('td');
            const link = element('a', row.server.name || row.server.ip_address, 'load-server-name fw-semibold');
            link.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(row.server.id));
            server.append(link, element('span', row.server.ip_address, 'load-detail'));
            tr.append(server);
            const state = element('td', undefined, 'load-state');
            const stateClass = row.error ? 'text-danger' : row.stats ? (row.partial ? 'text-warning' : 'text-success') : 'text-body-secondary';
            state.append(element('span', row.error ? t.failed : row.stats ? (row.partial ? t.partial : t.ready) : (row.checking ? t.checking : t.waiting), stateClass));
            if (row.error) state.append(element('span', row.error, 'load-detail'));
            tr.append(state);
            const stats = row.stats || {};
            tr.append(metricCell(stats.cpu));
            tr.append(metricCell(stats.memory, stats.memory && `${bytes(stats.memory.used_bytes)} / ${bytes(stats.memory.total_bytes)}`));
            tr.append(metricCell(stats.disk, stats.disk && `${t.free}: ${bytes(stats.disk.available_bytes)} / ${bytes(stats.disk.total_bytes)}`));
            const load = element('td', '—');
            if (stats.load) {
                load.textContent = stats.load.averages.map(n => loadNumber.format(n)).join(' / ');
                load.className = 'text-nowrap';
                load.append(element('span', `${t.cores}: ${stats.load.cores} · ${loadNumber.format(stats.load.per_core)} ${t.perCore}`, 'load-detail'));
                if (stats.load.per_core >= 1) load.classList.add('text-warning');
            }
            tr.append(load);
            const network = element('td', '—', 'text-nowrap');
            if (stats.network) {
                network.textContent = `↓ ${bytes(stats.network.rx_bytes_per_second)}${t.perSecond}`;
                network.append(element('span', `↑ ${bytes(stats.network.tx_bytes_per_second)}${t.perSecond}`, 'load-detail'));
                network.title = stats.network.interfaces.join(', ');
            }
            tr.append(network, element('td', stats.checked_at ? new Date(stats.checked_at * 1000).toLocaleTimeString(document.documentElement.lang) : '—', 'text-nowrap text-body-secondary'));
            body.append(tr);
        }
    }

    function showProgress() {
        const done = rows.filter(row => row.stats || row.error).length;
        const ok = rows.filter(row => row.stats).length;
        progress.textContent = t.progress.replace('{done}', done).replace('{total}', rows.length).replace('{ok}', ok).replace('{errors}', done - ok);
    }

    async function getJSON(url, pass) {
        const controller = new AbortController();
        const cancel = () => controller.abort();
        pass.signal.addEventListener('abort', cancel, {once: true});
        let timedOut = false;
        const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 40000);
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

    async function start() {
        if (run) return;
        const pass = new AbortController();
        run = pass;
        refresh.disabled = true;
        rows = [];
        body.replaceChildren();
        progress.textContent = t.loading;
        body.setAttribute('aria-busy', 'true');
        try {
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            rows = inventory.servers.map(server => ({server}));
            render(); showProgress();
            let next = 0;
            async function worker() {
                while (run === pass && next < rows.length) {
                    const row = rows[next++];
                    row.checking = true; render();
                    try {
                        const data = await getJSON(config.snapshotUrl.replace('__SERVER__', encodeURIComponent(row.server.id)), pass);
                        if (run !== pass) return;
                        row.stats = data.stats;
                        row.partial = ['cpu', 'memory', 'disk', 'load', 'network'].some(key => !data.stats[key]);
                    } catch (error) {
                        if (run !== pass) return;
                        row.error = error.message;
                    }
                    row.checking = false;
                    render(); showProgress();
                }
            }
            await Promise.all(Array.from({length: Math.min(4, rows.length)}, worker));
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
    filter.addEventListener('input', render);
    modal.querySelectorAll('[data-load-sort]').forEach(button => button.addEventListener('click', () => {
        const key = button.dataset.loadSort;
        sort = {key, direction: sort.key === key ? -sort.direction : key === 'name' ? 1 : -1};
        modal.querySelectorAll('th[aria-sort]').forEach(th => th.removeAttribute('aria-sort'));
        button.closest('th').setAttribute('aria-sort', sort.direction === 1 ? 'ascending' : 'descending');
        render();
    }));
})();
