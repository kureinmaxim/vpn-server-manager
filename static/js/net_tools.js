(() => {
    'use strict';
    const form = document.getElementById('net-tool-form');
    if (form) form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = document.getElementById('net-run');
        if (button.disabled) return;
        const label = button.textContent;
        const error = document.getElementById('net-error');
        const result = document.getElementById('net-result');
        button.disabled = true;
        button.textContent = form.dataset.running;
        error.hidden = true;
        result.hidden = true;
        result.setAttribute('aria-busy', 'true');
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 60000);
        try {
            const response = await fetch(form.dataset.endpoint, {
                method: 'POST', credentials: 'same-origin', signal: controller.signal,
                headers: {'Content-Type': 'application/json', 'X-Net-Tools-Token': form.dataset.token},
                body: JSON.stringify(Object.fromEntries(new FormData(form)))
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || form.dataset.failure);
            document.getElementById('net-output').textContent = JSON.stringify(data.result, null, 2);
            result.hidden = false;
        } catch (failure) {
            error.textContent = failure.name === 'AbortError' || failure instanceof SyntaxError || failure instanceof TypeError
                ? form.dataset.failure : failure.message;
            error.hidden = false;
        } finally {
            clearTimeout(timer);
            button.disabled = false;
            button.textContent = label;
            result.setAttribute('aria-busy', 'false');
        }
    });
    document.querySelectorAll('.net-saved').forEach(select => select.addEventListener('change', () => {
        if (!select.value) return;
        const input = document.getElementById(select.dataset.target);
        input.value = select.dataset.prefix + select.value;
        select.value = '';
        input.focus();
    }));
    document.querySelectorAll('[data-port]').forEach(button => button.addEventListener('click', () => {
        const input = document.getElementById('net-port');
        input.value = button.dataset.port;
        input.focus();
    }));
    document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
        const status = document.getElementById('net-copy-status');
        const text = document.getElementById(button.dataset.copy).textContent;
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
                } finally { area.remove(); button.focus(); }
            }
            status.textContent = status.dataset.copied;
        } catch (_) { status.textContent = status.dataset.failed; }
    }));
})();
