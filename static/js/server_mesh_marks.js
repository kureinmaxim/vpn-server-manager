(function () {
    const config = window.SERVER_MESH_MARKS;
    const board = document.getElementById('server-board');
    if (!config || !board) return;
    const t = config.i18n || {};

    function norm(value) {
        return String(value || '').trim().toLowerCase().replace(/\.$/, '');
    }

    function tokens(name) {
        return new Set(norm(name).split(/[\s_./-]+/).filter(part => part.length >= 3));
    }

    function nodeMatches(ip, name, node) {
        const address = norm(ip);
        const label = norm(name);
        const names = new Set([norm(node.name), norm(node.dns).split('.')[0]].filter(Boolean));
        const ips = [...(node.ips || []), ...(node.endpoints || [])].map(norm);
        if (address && ips.includes(address)) return true;
        if (address && address === norm(node.dns)) return true;
        const cur = norm(node.cur_addr);
        if (address && cur && (cur === address || cur.startsWith(address + ':') || cur.startsWith('[' + address + ']'))) {
            return true;
        }
        if (!label) return false;
        const parts = tokens(name);
        return names.has(label) || [...names].some(item => parts.has(item));
    }

    function isCoordinator(ip, mesh) {
        const address = norm(ip);
        if (!address || !mesh.coordinator) return false;
        return address === norm(mesh.coordinator) || (mesh.coordinator_ips || []).map(norm).includes(address);
    }

    function mark(kind, icon, title) {
        const el = document.createElement('span');
        el.className = 'badge rounded-pill server-mesh-mark ' + kind;
        el.title = title;
        const i = document.createElement('i');
        i.className = 'bi ' + icon;
        i.setAttribute('aria-hidden', 'true');
        const sr = document.createElement('span');
        sr.className = 'visually-hidden';
        sr.textContent = title;
        el.append(i, sr);
        return el;
    }

    function fill(holder, ip, name, mesh) {
        const matches = (mesh.nodes || []).filter(node => nodeMatches(ip, name, node));
        const peer = matches.length === 1 ? matches[0] : null;
        const bits = [];
        if (isCoordinator(ip, mesh)) {
            bits.push(mark('is-coord', 'bi-hdd-network-fill', t.coordinator + '. ' + t.coordinatorHint));
        }
        if (peer) {
            const who = peer.name || peer.dns || '';
            let meshTitle = t.meshMember + (who ? ': ' + who : '');
            if (!peer.online) meshTitle += ' · ' + t.meshOffline;
            bits.push(mark('is-mesh' + (peer.online ? '' : ' is-offline'), 'bi-diagram-3-fill', meshTitle));
            if (peer.exit_selected) {
                bits.push(mark('is-exit', 'bi-box-arrow-right', t.meshSelected));
            } else if (peer.exit_available) {
                bits.push(mark('is-exit-ready', 'bi-box-arrow-right', t.meshExit));
            }
            if (peer.relay) {
                bits.push(mark('is-derp', 'bi-broadcast-pin', (t.peerHome || '').replace('{region}', peer.relay) + (t.peerHomeHint ? '. ' + t.peerHomeHint : '')));
            }
        }
        holder.replaceChildren(...bits);
        holder.hidden = !bits.length;
    }

    fetch(config.url, {cache: 'no-store', headers: {Accept: 'application/json'}})
        .then(response => {
            if (response.status === 401) return null;
            return response.ok ? response.json() : null;
        })
        .then(mesh => {
            if (!mesh || mesh.state !== 'ready') return;
            board.querySelectorAll('.server-board-item').forEach(item => {
                const ip = item.getAttribute('data-ip') || '';
                const name = item.getAttribute('data-name') || '';
                item.querySelectorAll('.server-mesh-marks').forEach(holder => fill(holder, ip, name, mesh));
            });
        })
        .catch(() => { /* Tailscale missing: cards stay without marks. */ });
})();
