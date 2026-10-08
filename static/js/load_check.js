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
    let mesh = null;
    let derp = null;
    const pathRequests = new Set();
    let completedAt = null;
    const meshSummary = document.getElementById('load-check-mesh');
    const derpSummary = document.getElementById('load-check-derp');

    const truth = value => value === true ? t.yes : value === false ? t.no : t.unknown;

    function cancelPaths() {
        pathRequests.forEach(pass => pass.abort());
        pathRequests.clear();
    }

    async function checkPath(row, peer) {
        if (row.pathChecking) return;
        const pass = new AbortController();
        pathRequests.add(pass);
        row.pathChecking = true;
        render();
        try {
            const data = await getJSON(config.peerPathUrl.replace('__NODE__', encodeURIComponent(peer.id)), pass, 15000);
            if (!pass.signal.aborted && rows.includes(row)) row.path = data;
        } catch (error) {
            if (!pass.signal.aborted && rows.includes(row)) row.path = {state: 'unknown', error: error.message};
        } finally {
            pathRequests.delete(pass);
            row.pathChecking = false;
            if (!pass.signal.aborted && rows.includes(row)) render();
        }
    }

    function renderDerp() {
        derpSummary.replaceChildren();
        if (!derp || derp.state !== 'ready') {
            derpSummary.textContent = derp ? t.derpUnavailable : t.derpLoading;
            return;
        }
        const home = mesh && mesh.state === 'ready' ? mesh.home_relay : derp.home_relay;
        derpSummary.append(element('div', `${t.homeDerp}: ${home || '—'} · UDP: ${truth(derp.udp)} · ${t.preferredDerp}: ${derp.preferred || '—'}`));
        if (derp.exit_selected) derpSummary.append(element('div', t.exitWarning.replace('{name}', derp.exit_name || '—'), 'text-warning'));
        const regions = element('div', undefined, 'd-flex flex-wrap gap-2 mt-2');
        for (const region of derp.regions || []) {
            const latency = region.latency_ms === null ? t.unknown : region.latency_ms.toLocaleString(locale, {maximumFractionDigits: 1}) + ' ' + t.ms;
            const badge = element('span', `${region.own ? t.own + ' ' : ''}${region.code}: ${latency}`, region.own ? 'badge text-bg-info' : 'badge text-bg-secondary');
            badge.title = `${region.name} (${region.id}) · ${region.hosts.join(', ')}`;
            regions.append(badge);
        }
        derpSummary.append(regions);
        derpSummary.append(element('div', t.derpCache.replace('{time}', new Date(derp.checked_at * 1000).toLocaleTimeString(locale)), 'text-body-secondary mt-1'));
    }

    function remoteDerpDetails(row, cell) {
        const data = row.derp;
        if (!data || data.state !== 'ready') {
            cell.append(element('span', data ? t.derpUnavailable : t.derpLoading, 'load-detail'));
            return;
        }
        const cfg = data.config;
        if (cfg && cfg.enabled === true) {
            const nodes = mesh && mesh.state === 'ready' ? mesh.nodes : [];
            const used = nodes.some(node => node.relay && node.relay === cfg.region_code);
            const healthy = data.probe_code === 200 && data.stun_listening === true;
            const failed = data.probe_code !== null && data.probe_code !== 200 || data.stun_listening === false;
            const role = failed ? t.derpFailed : healthy ? (used ? t.derpPrimary : mesh && mesh.state === 'ready' ? t.derpStandby : t.unknown) : t.unknown;
            cell.append(element('span', `${t.ownDerp} ${cfg.region_code || '—'} (${cfg.region_id ?? '—'}) — ${role}`,
                'badge d-block mt-1 ' + (failed ? 'text-bg-warning' : healthy ? 'text-bg-info' : 'text-bg-secondary')));
        }
        const details = element('details', undefined, 'load-detail');
        details.append(element('summary', t.derpDetails));
        details.append(element('div', `Headscale: ${truth(data.headscale)} ${data.version || ''}`));
        if (cfg) {
            details.append(element('div', `${t.derpEnabled}: ${truth(cfg.enabled)} · verify_clients: ${truth(cfg.verify_clients)}`));
            details.append(element('div', `/derp/probe: ${data.probe_code ?? '—'} · STUN ${data.stun_port ?? '—'}: ${truth(data.stun_listening)}`));
            details.append(element('div', `${t.publicMap}: ${truth(cfg.public_map)}`));
        } else details.append(element('div', t.derpConfigUnknown));
        details.append(element('div', `${t.publicIpv4}: ${truth(data.public_ipv4)} · UDP 3478 ${data.udp3478_busy === true ? t.busy : data.udp3478_busy === false ? t.freePort : t.unknown}`));
        details.append(element('div', data.tcp443_busy === true
            ? t.portConflict.replace('{owner}', data.tcp443_owner || t.unknown)
            : `TCP 443: ${data.tcp443_busy === false ? t.freePort : t.unknown}`));
        details.append(element('div', t.derpCandidateHint));
        cell.append(details);
    }

    function meshCell(row) {
        const cell = element('td', undefined, 'load-mesh');
        const address = (row.server.ip_address || '').toLowerCase().replace(/\.$/, '');
        const remote = row.stats && row.stats.mesh;
        const identity = remote && remote.state === 'ready' && remote.self;
        const nodes = mesh && mesh.state === 'ready' ? mesh.nodes : [];
        const matches = nodes.filter(node => identity && identity.id
            ? node.id === identity.id
            : node.ips.includes(address) || (node.dns && node.dns.toLowerCase() === address));
        const peer = matches.length === 1 ? matches[0] : null;
        if (mesh && mesh.coordinator && (address === mesh.coordinator.toLowerCase() || (mesh.coordinator_ips || []).includes(address))) {
            const badge = element('span', t.coordinator, 'badge text-bg-primary d-block mb-1');
            badge.title = t.coordinatorHint; cell.append(badge);
        }
        cell.append(element('span', peer ? t.meshMember : mesh && mesh.state === 'ready' && identity ? t.meshOther : t.meshUnknown, peer ? 'text-success' : 'text-body-secondary'));
        if (peer) {
            cell.append(element('span', peer.exit_selected ? t.meshSelected : peer.exit_available ? t.meshExit : t.meshNode,
                'badge d-block mt-1 ' + (peer.exit_selected ? 'text-bg-success' : peer.exit_available ? 'text-bg-info' : 'text-bg-secondary')));
            cell.append(element('span', peer.ips.join(', '), 'load-detail'));
            if (!peer.online) cell.append(element('span', t.meshOffline, 'load-detail text-warning'));
            if (!row.path || !['direct', 'relay'].includes(row.path.state)) {
                cell.append(element('span', peer.cur_addr ? t.statusAddress.replace('{address}', peer.cur_addr) : t.pathUnconfirmed, 'load-detail'));
            }
            if (peer.relay) cell.append(element('span', t.peerHome.replace('{region}', peer.relay), 'load-detail'));
            if (row.path) {
                const path = row.path;
                cell.append(element('span', path.state === 'direct' ? t.directPath.replace('{address}', path.address)
                    : path.state === 'relay' ? t.relayPath.replace('{region}', path.relay) : t.pathUnknown, 'load-detail text-info'));
                if (path.checked_at) cell.append(element('span', 'ping: ' + new Date(path.checked_at * 1000).toLocaleTimeString(locale), 'load-detail'));
                if (path.error) cell.append(element('span', path.error, 'load-detail text-warning'));
            }
            const ping = element('button', row.pathChecking ? t.checking : t.checkPath, 'btn btn-sm btn-outline-secondary mt-1');
            ping.type = 'button'; ping.disabled = !!row.pathChecking; ping.title = t.pathHint;
            ping.addEventListener('click', () => checkPath(row, peer));
            cell.append(ping);
        }
        remoteDerpDetails(row, cell);
        return cell;
    }
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
            tr.append(meshCell(row));
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
            tr.append(network);
            body.append(tr);
        }
    }

    function showProgress() {
        const done = rows.filter(row => row.stats || row.error).length;
        const ok = rows.filter(row => row.stats).length;
        progress.textContent = t.progress.replace('{done}', done).replace('{total}', rows.length).replace('{ok}', ok).replace('{errors}', done - ok);
        if (completedAt) progress.textContent += ' · ' + t.completed.replace('{time}', completedAt.toLocaleTimeString(locale));
    }

    async function getJSON(url, pass, timeout = 40000) {
        const controller = new AbortController();
        if (pass.signal.aborted) throw new DOMException('Aborted', 'AbortError');
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

    async function start() {
        if (run) return;
        cancelPaths();
        const pass = new AbortController();
        run = pass;
        refresh.disabled = true;
        rows = [];
        mesh = null;
        derp = null;
        renderDerp();
        completedAt = null;
        meshSummary.textContent = t.meshLoading;
        body.replaceChildren();
        progress.textContent = t.loading;
        body.setAttribute('aria-busy', 'true');
        try {
            const meshRequest = getJSON(config.meshUrl, pass).then(data => {
                if (run !== pass) return;
                mesh = data;
                meshSummary.textContent = data.state === 'ready'
                    ? `${t.meshHost}: ${data.name || '—'} / ${data.host || '—'} · ${t.coordinator}: ${data.coordinator || '—'}`
                    : t.meshUnavailable;
                render(); renderDerp();
            }).catch(() => { if (run === pass) meshSummary.textContent = t.meshUnavailable; });
            const derpRequest = getJSON(config.derpUrl, pass, 15000).then(data => {
                if (run !== pass) return;
                derp = data; renderDerp();
            }).catch(() => {
                if (run === pass) { derp = {state: 'unavailable'}; renderDerp(); }
            });
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            rows = inventory.servers.map(server => ({server}));
            render(); showProgress();
            let nextDerp = 0;
            async function derpWorker() {
                while (run === pass && nextDerp < rows.length) {
                    const row = rows[nextDerp++];
                    try {
                        const data = await getJSON(config.derpSnapshotUrl.replace('__SERVER__', encodeURIComponent(row.server.id)), pass, 22000);
                        if (run !== pass) return;
                        row.derp = data.stats;
                    } catch (_) {
                        if (run !== pass) return;
                        row.derp = {state: 'unavailable'};
                    }
                    render();
                }
            }
            const remoteDerpRequest = Promise.all(Array.from({length: Math.min(2, rows.length)}, derpWorker));
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
            if (run === pass) {
                completedAt = new Date();
                showProgress();
            }
            await Promise.all([meshRequest, derpRequest, remoteDerpRequest]);
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
        cancelPaths();
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
