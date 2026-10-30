(() => {
    'use strict';
    const panel = document.querySelector('[data-ssh-config-import]');
    if (!panel) return;

    const button = panel.querySelector('[data-import-ssh-config]');
    const select = panel.querySelector('[data-ssh-config-alias]');
    const status = panel.querySelector('[data-ssh-config-status]');
    const messages = new Map([
        ['loading', panel.dataset.loading],
        ['selectAlias', panel.dataset.selectAlias],
        ['noHosts', panel.dataset.noHosts],
        ['imported', panel.dataset.imported],
        ['ignored', panel.dataset.ignored],
        ['error', panel.dataset.error]
    ]);
    let hosts = [];
    let globalUnsupported = [];

    const showIgnored = items => {
        if (!items || !items.length) return '';
        return ' ' + messages.get('ignored') + ': ' + items.join(', ') + '.';
    };

    button.addEventListener('click', async () => {
        button.disabled = true;
        status.textContent = messages.get('loading');
        try {
            const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
            const response = await fetch(panel.dataset.url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
                body: '{}',
                cache: 'no-store'
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || messages.get('error'));

            hosts = Array.isArray(result.hosts) ? result.hosts : [];
            globalUnsupported = Array.isArray(result.unsupported) ? result.unsupported : [];
            select.replaceChildren();
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = messages.get('selectAlias');
            select.append(placeholder);
            hosts.forEach((host, index) => {
                const option = document.createElement('option');
                option.value = String(index);
                option.textContent = host.alias + ' → ' + (host.user ? host.user + '@' : '')
                    + host.host_name + ':' + host.port;
                select.append(option);
            });
            select.disabled = hosts.length === 0;
            select.hidden = hosts.length === 0;
            status.textContent = (hosts.length ? '' : messages.get('noHosts'))
                + showIgnored(globalUnsupported);
        } catch (error) {
            status.textContent = error instanceof Error ? error.message : messages.get('error');
        } finally {
            button.disabled = false;
        }
    });

    select.addEventListener('change', () => {
        if (select.value === '') return;
        const host = hosts[Number(select.value)];
        if (!host) return;
        const form = panel.closest('form');
        const fill = (name, value) => {
            const field = form?.elements.namedItem(name);
            if (field && value !== null && value !== undefined) field.value = String(value);
        };
        fill('name', host.alias);
        fill('ip_address', host.host_name);
        fill('ssh_user', host.user);
        fill('ssh_port', host.port);
        if (host.identity_file) fill('ssh_key', host.identity_file);

        const endpoint = (host.user ? host.user + '@' : '') + host.host_name + ':' + host.port;
        status.textContent = messages.get('imported') + ': ' + host.alias + ' — ' + endpoint + '.'
            + showIgnored([...new Set(globalUnsupported.concat(host.unsupported || []))]);
    });
})();
