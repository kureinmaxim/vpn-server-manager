(function () {
    const root = document.getElementById('own-dns');
    const config = window.OWN_DNS;
    if (!root || !config) return;
    const t = config.i18n;
    const $ = id => document.getElementById(id);
    const status = $('own-dns-status');
    const cards = $('own-dns-cards');
    const guide = $('own-dns-guide');
    const which = $('own-dns-which');
    const refresh = $('own-dns-refresh');
    const dohInput = $('own-doh-url');
    const locale = document.documentElement.lang || undefined;
    const stateClass = {running: 'text-bg-success', partial: 'text-bg-warning', stopped: 'text-bg-danger', unknown: 'text-bg-secondary'};
    const CACHE_KEY = 'own-dns-v2';
    const CACHE_MS = 10 * 60 * 1000;
    const desktop = Boolean(window.pywebview);
    let run = null;
    let found = [];
    let doh = null;
    let pickedMode = null;

    async function getJSON(url, pass, timeout = 30000) {
        const controller = new AbortController();
        const cancel = () => controller.abort();
        pass.signal.addEventListener('abort', cancel, {once: true});
        let timedOut = false;
        const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
        try {
            const response = await fetch(url, {signal: controller.signal, cache: 'no-store', headers: {Accept: 'application/json'}});
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

    function isTailnet(ip) {
        const value = String(ip || '').toLowerCase();
        if (value.startsWith('fd7a:115c:a1e0:')) return true;
        const parts = value.split('.').map(Number);
        return parts.length === 4 && parts[0] === 100 && parts[1] >= 64 && parts[1] <= 127;
    }
    const isLoopback = ip => /^127\./.test(ip) || ip === '::1' || ip === 'localhost';
    const isWildcard = ip => ['', '*', '0.0.0.0', '::'].includes(ip);

    function tailnetAddress(server, nodes) {
        if (isTailnet(server.ip_address)) return server.ip_address;
        const address = (server.ip_address || '').toLowerCase().replace(/\.$/, '');
        const hits = (nodes || []).filter(node => (node.ips || []).includes(server.ip_address)
            || (node.dns && node.dns.toLowerCase() === address));
        return hits.length === 1 ? (hits[0].ips || []).find(ip => /^\d/.test(ip) && isTailnet(ip)) || '' : '';
    }

    // Docker "Ports": "127.0.0.1:5300->53/udp, [::]:53->53/tcp, :::53->53/tcp, 3000/tcp"
    function parsePublish(item) {
        const arrow = item.match(/^(.*)->(\d+)(?:-\d+)?\/(tcp|udp)$/i);
        if (!arrow) return null;
        const left = arrow[1].match(/^(.*):(\d+)(?:-\d+)?$/);
        if (!left) return null;
        let host = left[1];
        if (host.startsWith('[') && host.endsWith(']')) host = host.slice(1, -1);
        if (host === '' || host === ':') host = '::';
        return {host, hostPort: Number(left[2]), port: Number(arrow[2]), proto: arrow[3].toLowerCase()};
    }

    function mappings(role) {
        const result = [];
        for (const part of role.components || []) {
            for (const item of String(part.ports || '').split(',')) {
                const parsed = parsePublish(item.trim());
                if (parsed) result.push(parsed);
            }
        }
        return result;
    }

    function analyse(item) {
        const maps = mappings(item.role);
        const dns = maps.filter(m => m.port === 53);
        const sockets = (item.role.listeners || []).filter(s => s.port === 53)
            .map(s => ({host: s.address, hostPort: 53, port: 53, proto: s.proto || 'udp'}));
        const all = dns.concat(sockets);
        const reachable = all.filter(s => !isLoopback(s.host));
        const loop = all.find(s => isLoopback(s.host));
        let exposure = 'unknown';
        let dnsIp = '';
        const ts = reachable.find(s => isTailnet(s.host));
        if (reachable.some(s => isWildcard(s.host))) { exposure = 'public'; dnsIp = item.address || ''; }
        else if (ts) { exposure = 'tailnet'; dnsIp = ts.host; }
        else if (reachable.length) { exposure = 'lan'; dnsIp = reachable[0].host; }
        else if (all.length || item.role.listeners_known) exposure = 'local';
        const dot = (item.role.listeners || []).some(s => s.port === 853 && !isLoopback(s.address));
        const web = maps.filter(m => m.proto === 'tcp' && [80, 3000, 8080].includes(m.port))
            .sort((a, b) => (a.port === 80 ? 0 : 1) - (b.port === 80 ? 0 : 1))[0];
        return {exposure, dnsIp, dot, web, loop};
    }

    function setText(selector, text) {
        root.querySelectorAll(selector).forEach(node => { node.textContent = text; });
    }

    function currentMode() {
        return (root.querySelector('input[name="own-mode"]:checked') || {}).value || 'doh';
    }

    function applyMode() {
        const mode = currentMode();
        root.querySelectorAll('[data-mode]').forEach(node => { node.hidden = node.dataset.mode !== mode; });
    }

    function applyItem() {
        const item = found.find(row => row.server.id === which.value) || found[0];
        if (!item) return;
        const info = item.info;
        const note = $('own-dns-mode-note');
        const warn = $('own-dns-mode-warn');
        warn.hidden = true;
        const loopText = info.loop ? `${info.loop.host || info.loop.address}:${info.loop.hostPort || info.loop.port}` : '127.0.0.1';
        note.textContent = {
            local: t.modeLocal.replace('{where}', loopText),
            tailnet: t.modeTailnet.replace('{address}', info.dnsIp),
            lan: t.modeLan.replace('{address}', info.dnsIp),
            public: t.modePublic,
            unknown: t.modeUnknown,
        }[info.exposure];
        if (info.exposure === 'public') { warn.textContent = t.openResolver; warn.hidden = false; }
        const ip = info.dnsIp || item.address || '';
        setText('.own-ip', ip || t.addressMissing);
        const ipOk = ['tailnet', 'lan'].includes(info.exposure) || (info.exposure === 'public' && ip);
        $('own-mode-ip').disabled = !ipOk;
        if (!pickedMode) $('own-mode-' + (ipOk ? 'ip' : 'doh')).checked = true;
        else if (!ipOk && currentMode() === 'ip') $('own-mode-doh').checked = true;
        applyMode();
        $('own-android-dot').hidden = !info.dot;

        const ssh = (config.ssh || {})[item.server.id] || {};
        const target = `${ssh.user || 'root'}@${item.server.ip_address}`;
        const portArg = ssh.port && Number(ssh.port) !== 22 ? `-p ${ssh.port} ` : '';
        const panelWarn = $('own-panel-warn');
        panelWarn.hidden = true;
        let panel = 'unknown';
        if (info.web) {
            if (isTailnet(info.web.host)) {
                panel = 'tailnet';
                setText('.own-panel-direct', `http://${info.web.host}:${info.web.hostPort}`);
            } else {
                panel = 'tunnel';
                const remote = isLoopback(info.web.host) ? info.web.host : '127.0.0.1';
                setText('.own-ssh', `ssh -N -o ExitOnForwardFailure=yes ${portArg}-L 127.0.0.1:13001:${remote}:${info.web.hostPort} ${target}`);
                if (!isLoopback(info.web.host)) {
                    panelWarn.textContent = t.panelExposed.replace('{port}', info.web.hostPort);
                    panelWarn.hidden = false;
                }
            }
        }
        genericTunnel = {prefix: `ssh -N -o ExitOnForwardFailure=yes ${portArg}-L 127.0.0.1:13001:127.0.0.1:`, target};
        applyGenericTunnel();
        root.querySelectorAll('[data-panel]').forEach(node => { node.hidden = node.dataset.panel !== panel; });
        applyDoh(item);
        applyIp(ip);
    }

    let genericTunnel = null;

    function applyGenericTunnel() {
        if (!genericTunnel) return;
        const field = $('own-panel-port');
        const port = Number(field && field.value);
        setText('.own-ssh-generic', `${genericTunnel.prefix}${Number.isInteger(port) && port >= 1 && port <= 65535 ? port : 3000} ${genericTunnel.target}`);
    }

    function applyIp(ip) {
        const value = ip || 'IP';
        setText('.own-linux-ip', `nmcli connection modify NAME ipv4.dns ${value} ipv4.ignore-auto-dns yes && nmcli connection up NAME`);
        setText('.own-wrt-ip', `uci add_list dhcp.@dnsmasq[0].server='${value}' && uci set dhcp.@dnsmasq[0].noresolv='1' && uci commit dhcp && service dnsmasq restart`);
        setText('.own-wrt-one', `uci add dhcp host && uci set dhcp.@host[-1].mac='AA:BB:CC:DD:EE:FF' && uci set dhcp.@host[-1].tag='owndns' && uci set dhcp.owndns=tag && uci add_list dhcp.owndns.dhcp_option='6,${value}' && uci commit dhcp && service dnsmasq restart`);
    }

    function dohHostIp(host, item) {
        const records = (config.hosts || {})[host] || [];
        const v4 = records.find(ip => /^\d+\.\d+\.\d+\.\d+$/.test(ip));
        if (v4) return v4;
        const server = item && item.server.ip_address;
        return server && /^\d+\.\d+\.\d+\.\d+$/.test(server) && !isTailnet(server) ? server : '';
    }

    function applyDoh(item) {
        item = item || found.find(row => row.server.id === which.value) || found[0];
        const raw = dohInput.value.trim();
        let url = null;
        try {
            const parsed = new URL(raw);
            if (parsed.protocol === 'https:' && parsed.hostname) url = parsed;
        } catch (error) { url = null; }
        $('own-doh-invalid').hidden = !raw || Boolean(url);
        doh = url ? url.href : null;
        const shown = doh || t.dohPlaceholder;
        const ip = url ? dohHostIp(url.hostname.toLowerCase(), item) : '';
        setText('.own-doh', shown);
        setText('.own-doh-ip', ip || (url ? t.dohIpUnknown.replace('{host}', url.hostname) : t.dohIpHint));
        const ipArg = ip || 'IP';
        setText('.own-win-doh', `Add-DnsClientDohServerAddress -ServerAddress ${ipArg} -DohTemplate '${doh || 'URL'}' -AllowFallbackToUdp $False -AutoUpgrade $True`);
        setText('.own-win-set', `Set-DnsClientServerAddress -InterfaceAlias "Wi-Fi" -ServerAddresses ${ipArg}`);
        setText('.own-linux-proxy', `dnsproxy -l 127.0.0.1 -p 5353 -u '${doh || 'URL'}' -b 9.9.9.9:53`);
        setText('.own-mihomo', `dns:\n  default-nameserver: [9.9.9.9, 1.1.1.1]\n  proxy-server-nameserver: [9.9.9.9, 1.1.1.1]\n  nameserver: ['${doh || 'URL'}']`);
        root.querySelectorAll('.own-profile-copy, .own-profile-download').forEach(button => { button.disabled = !doh; });
    }

    function uuid() {
        if (window.crypto && crypto.randomUUID) return crypto.randomUUID().toUpperCase();
        const bytes = crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
        const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`.toUpperCase();
    }

    function profile() {
        const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const inner = uuid();
        const outer = uuid();
        return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>DNSSettings</key>
            <dict>
                <key>DNSProtocol</key>
                <string>HTTPS</string>
                <key>ServerURL</key>
                <string>${xml(doh)}</string>
            </dict>
            <key>PayloadDisplayName</key>
            <string>Own DNS (DoH)</string>
            <key>PayloadIdentifier</key>
            <string>local.vpnmanager.owndns.${inner}</string>
            <key>PayloadType</key>
            <string>com.apple.dnsSettings.managed</string>
            <key>PayloadUUID</key>
            <string>${inner}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>Own DNS</string>
    <key>PayloadIdentifier</key>
    <string>local.vpnmanager.owndns</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>${outer}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
`;
    }

    async function copyText(text, button) {
        try {
            if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
            else {
                const area = document.createElement('textarea');
                area.value = text;
                area.style.position = 'fixed';
                area.style.opacity = '0';
                document.body.appendChild(area);
                try {
                    area.select();
                    if (!document.execCommand('copy')) throw new Error('copy');
                } finally { area.remove(); }
            }
            flash(button, t.copied);
        } catch (error) { flash(button, t.copyFailed); }
    }

    function flash(button, text) {
        const previous = button.getAttribute('title');
        button.setAttribute('title', text);
        button.classList.add('own-copied');
        setTimeout(() => { button.classList.remove('own-copied'); if (previous) button.setAttribute('title', previous); }, 1500);
    }

    function fromSaved(row) {
        const vps = (config.vps || []).find(server => String(server.id) === String(row.server_id)) || {};
        const ip = row.dns_ip || vps.ip_address || '';
        const port = Number(row.panel_port) || 3001;
        const web = {
            host: row.panel_via === 'tailnet' ? (row.dns_ip || ip || '100.64.0.1') : '127.0.0.1',
            hostPort: port, port, proto: 'tcp'
        };
        return {
            ownId: row.id,
            live: false,
            server: {id: row.server_id || '', name: row.name, ip_address: ip},
            role: {
                state: row.last_state || 'unknown',
                components: [],
                last_check: row.last_seen ? {state: row.last_state || 'unknown', checked_at: row.last_seen, stale: true} : null
            },
            address: row.exposure === 'tailnet' ? row.dns_ip : '',
            info: {
                exposure: row.exposure || 'unknown',
                dnsIp: row.dns_ip || '',
                dot: false,
                web,
                loop: row.exposure === 'local' ? {host: '127.0.0.1', hostPort: 53, port: 53} : null
            }
        };
    }

    function matchSaved(serverId, list) {
        return (list || found).find(item => item.server.id && String(item.server.id) === String(serverId));
    }

    async function persist(item) {
        if (!config.saveUrl || !item.server.id) return;
        try {
            const response = await fetch(config.saveUrl, {
                method: 'POST',
                cache: 'no-store',
                headers: {'Accept': 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': config.csrf},
                body: JSON.stringify({
                    server_id: item.server.id,
                    name: item.server.name,
                    exposure: item.info.exposure,
                    dns_ip: item.info.dnsIp,
                    panel_port: item.info.web ? item.info.web.hostPort : 3001,
                    panel_via: item.info.web && isTailnet(item.info.web.host) ? 'tailnet' : 'tunnel',
                    last_state: item.role.state
                })
            });
            const data = await response.json().catch(() => ({}));
            if (response.ok && data.item && data.item.id) item.ownId = data.item.id;
        } catch (error) { /* keep the live card even if the file write fails */ }
    }

    function card(item) {
        const article = document.createElement('article');
        article.className = 'dns-provider own-dns-card';
        const header = document.createElement('div');
        header.className = 'd-flex justify-content-between align-items-start gap-2';
        const title = document.createElement('h3');
        title.className = 'text-truncate';
        title.textContent = item.server.name || item.server.ip_address;
        const badge = document.createElement('span');
        badge.className = 'badge flex-shrink-0 ' + (stateClass[item.role.state] || stateClass.unknown);
        const core = (item.role.components || []).filter(part => !part.optional);
        const active = core.filter(part => part.status === 'active').length;
        badge.textContent = (t[item.role.state] || t.unknown) + (core.length ? ` ${active}/${core.length}` : '');
        header.append(title, badge);
        article.append(header);
        const access = document.createElement('div');
        access.className = 'small';
        access.textContent = `${t.access}: ${t['access_' + item.info.exposure] || t.access_unknown}`;
        article.append(access);
        if (item.address) {
            const address = document.createElement('div');
            address.className = 'small text-body-secondary';
            address.textContent = `Tailscale: ${item.address}`;
            article.append(address);
        }
        if (!item.live && item.ownId) {
            const stale = document.createElement('div');
            stale.className = 'small text-body-secondary';
            stale.textContent = t.savedStale;
            article.append(stale);
        }
        (item.role.components || []).forEach(part => {
            const line = document.createElement('div');
            line.className = 'small text-body-secondary';
            const bits = [part.name];
            if (part.version) bits.push(part.version);
            if (part.status && part.status !== 'active') bits.push(part.status);
            line.textContent = bits.join(' · ');
            article.append(line);
        });
        const last = item.role.last_check;
        if (last) {
            const note = document.createElement('div');
            note.className = 'small';
            let text = `${t.lastCheck}: ${t[last.state] || t.unknown}`;
            if (last.checked_at) text += ' · ' + new Date(last.checked_at).toLocaleString(locale);
            if (last.stale) text += ' · ' + t.stale;
            note.textContent = text;
            article.append(note);
        }
        const actions = document.createElement('div');
        actions.className = 'dns-actions';
        if (item.ownId && config.editUrl) {
            const edit = document.createElement('a');
            edit.className = 'btn btn-sm btn-outline-secondary';
            edit.href = config.editUrl.replace('__OWN__', encodeURIComponent(item.ownId));
            edit.setAttribute('aria-label', t.edit);
            edit.title = t.edit;
            edit.innerHTML = '<i class="bi bi-pencil" aria-hidden="true"></i>';
            actions.append(edit);
        }
        if (item.server.id && (config.vps || []).some(server => String(server.id) === String(item.server.id))) {
            const diagnostics = document.createElement('a');
            diagnostics.className = 'btn btn-sm btn-outline-secondary';
            diagnostics.href = config.diagnosticsUrl.replace('__SERVER__', encodeURIComponent(item.server.id)) + '?role=adguard';
            diagnostics.textContent = t.diagnostics;
            const monitoring = document.createElement('a');
            monitoring.className = 'btn btn-sm btn-outline-secondary';
            monitoring.href = config.monitoringUrl.replace('__SERVER__', encodeURIComponent(item.server.id));
            monitoring.textContent = t.monitoring;
            actions.append(diagnostics, monitoring);
        }
        if (item.ownId && config.deleteUrl) {
            const form = document.createElement('form');
            form.method = 'post';
            form.action = config.deleteUrl.replace('__OWN__', encodeURIComponent(item.ownId));
            form.className = 'd-inline';
            form.addEventListener('submit', event => {
                if (!confirm(t.removeConfirm.replace('{name}', item.server.name || item.server.ip_address || ''))) {
                    event.preventDefault();
                }
            });
            const csrf = document.createElement('input');
            csrf.type = 'hidden';
            csrf.name = 'csrf_token';
            csrf.value = config.csrf || '';
            const button = document.createElement('button');
            button.type = 'submit';
            button.className = 'btn btn-sm btn-outline-danger';
            button.title = t.remove;
            button.setAttribute('aria-label', t.remove);
            button.innerHTML = '<i class="bi bi-trash" aria-hidden="true"></i>';
            form.append(csrf, button);
            actions.append(form);
        }
        article.append(actions);
        return article;
    }

    function render(text) {
        found.forEach(item => { if (item.live) item.info = analyse(item); });
        cards.replaceChildren(...found.map(card));
        guide.hidden = !found.length;
        $('own-dns-which-box').hidden = found.length < 2;
        const selected = which.value;
        which.replaceChildren(...found.map(item => {
            const option = document.createElement('option');
            option.value = item.server.id;
            option.textContent = item.server.name || item.server.ip_address;
            return option;
        }));
        if (found.some(item => item.server.id === selected)) which.value = selected;
        if (found.length) applyItem();
        status.textContent = text;
    }

    function save() {
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({at: Date.now(), found: found.map(({server, role, address}) => ({server, role, address}))})); }
        catch (error) { /* storage can be disabled */ }
    }

    function cached() {
        try {
            const data = JSON.parse(sessionStorage.getItem(CACHE_KEY) || 'null');
            return data && Date.now() - data.at < CACHE_MS ? data : null;
        } catch (error) { return null; }
    }

    async function start() {
        if (run) run.abort();
        const pass = new AbortController();
        run = pass;
        refresh.disabled = true;
        status.textContent = t.loading;
        const next = found.slice();
        try {
            const inventory = await getJSON(config.serversUrl, pass);
            if (run !== pass) return;
            const servers = inventory.servers || [];
            let nodes = [];
            try {
                const mesh = await getJSON(config.meshUrl, pass, 8000);
                if (mesh.state === 'ready') nodes = mesh.nodes || [];
            } catch (error) { nodes = []; }
            if (run !== pass) return;
            if (!servers.length) {
                render(next.length ? t.fromFile : t.empty);
                return;
            }
            const failed = [];
            let index = 0;
            let done = 0;
            async function worker() {
                while (run === pass && index < servers.length) {
                    const server = servers[index++];
                    try {
                        const data = await getJSON(config.rolesUrl.replace('__SERVER__', encodeURIComponent(server.id)), pass);
                        if (run !== pass) return;
                        const role = (data.stats || []).find(item => item.key === 'adguard' && item.detected);
                        if (role) {
                            const address = tailnetAddress(server, nodes);
                            let item = matchSaved(server.id, next);
                            if (!item) {
                                item = {server, role, address, ownId: '', live: true};
                                next.push(item);
                            } else {
                                item.server = server;
                                item.role = role;
                                item.address = address;
                                item.live = true;
                            }
                            item.info = analyse(item);
                            await persist(item);
                        }
                    } catch (error) {
                        if (run !== pass) return;
                        failed.push((server.name || server.ip_address) + (error.message ? ` (${error.message})` : ''));
                    }
                    done += 1;
                    status.textContent = t.progress.replace('{done}', done).replace('{total}', servers.length);
                }
            }
            await Promise.all(Array.from({length: Math.min(4, servers.length)}, worker));
            if (run !== pass) return;
            found = next.sort((a, b) => (a.server.name || '').localeCompare(b.server.name || ''));
            let text = found.length
                ? t.progress.replace('{done}', servers.length).replace('{total}', servers.length) + ' · ' + t.completed.replace('{time}', new Date().toLocaleTimeString(locale))
                : t.none;
            if (failed.length) text += ' ' + t.errors.replace('{names}', failed.join('; '));
            render(text);
            if (found.length) save();
        } catch (error) {
            if (run === pass) status.textContent = error.message;
        } finally {
            if (run === pass) { run = null; refresh.disabled = false; }
        }
    }

    function showTab(tab) {
        root.querySelectorAll('[data-own-tab]').forEach(button => {
            const on = button.dataset.ownTab === tab;
            button.setAttribute('aria-selected', on ? 'true' : 'false');
            const panel = $(button.getAttribute('aria-controls'));
            if (panel) panel.hidden = !on;
        });
    }

    function defaultTab() {
        const agent = navigator.userAgent || '';
        if (/iPhone|iPad/.test(agent)) return 'ios';
        if (/Android/.test(agent)) return 'android';
        if (/Mac OS X|Macintosh/.test(agent)) return 'macos';
        if (/Windows/.test(agent)) return 'windows';
        if (/Linux/.test(agent)) return 'linux';
        return 'panel';
    }

    root.querySelectorAll('[data-own-tab]').forEach(button => button.addEventListener('click', () => {
        showTab(button.dataset.ownTab);
        try { localStorage.setItem('own-dns-tab', button.dataset.ownTab); } catch (error) { /* ignore */ }
    }));
    root.querySelectorAll('[data-own-wrt]').forEach(button => button.addEventListener('click', () => {
        root.querySelectorAll('[data-own-wrt]').forEach(other => other.setAttribute('aria-pressed', other === button ? 'true' : 'false'));
        root.querySelectorAll('[data-wrt-panel]').forEach(panel => { panel.hidden = panel.dataset.wrtPanel !== button.dataset.ownWrt; });
    }));
    root.querySelectorAll('input[name="own-mode"]').forEach(input => input.addEventListener('change', () => {
        pickedMode = currentMode();
        applyMode();
    }));
    root.addEventListener('click', event => {
        const button = event.target.closest('.own-copy, .own-copy-pre');
        if (!button) return;
        const code = button.previousElementSibling;
        if (code) copyText(code.textContent, button);
    });
    root.querySelectorAll('.own-profile-copy').forEach(button => button.addEventListener('click', () => { if (doh) copyText(profile(), button); }));
    root.querySelectorAll('.own-profile-download').forEach(button => {
        button.hidden = desktop;
        button.addEventListener('click', () => {
            if (!doh) return;
            const link = document.createElement('a');
            link.href = URL.createObjectURL(new Blob([profile()], {type: 'application/x-apple-aspen-config'}));
            link.download = 'own-dns.mobileconfig';
            document.body.appendChild(link);
            link.click();
            setTimeout(() => { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
        });
    });
    dohInput.addEventListener('input', () => applyDoh());
    const panelPort = $('own-panel-port');
    if (panelPort) panelPort.addEventListener('input', applyGenericTunnel);
    which.addEventListener('change', applyItem);
    refresh.addEventListener('click', start);
    window.addEventListener('pagehide', () => { dohInput.value = ''; if (run) run.abort(); });

    let tab = null;
    try { tab = localStorage.getItem('own-dns-tab'); } catch (error) { tab = null; }
    showTab(root.querySelector(`[data-own-tab="${tab}"]`) ? tab : defaultTab());
    applyMode();
    found = (config.saved || []).map(fromSaved);
    if (found.length) render(t.fromFile);
    const cachedLive = cached();
    if (cachedLive && cachedLive.found && cachedLive.found.length) {
        cachedLive.found.forEach(live => {
            const item = live.server && live.server.id ? matchSaved(live.server.id) : null;
            if (item) {
                item.role = live.role;
                item.address = live.address;
                item.live = true;
            }
        });
        render(t.fromCache.replace('{time}', new Date(cachedLive.at).toLocaleTimeString(locale)));
    }
    start();
})();
