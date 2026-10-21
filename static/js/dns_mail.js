(() => {
    const form = document.getElementById('diagnostics-form');
    if (!form) return;
    const t = window.DIAGNOSTICS_LABELS;
    const message = document.getElementById('diagnostics-message');
    const output = document.getElementById('diagnostics-results');
    const role = form.elements.role;
    const colors = {healthy: 'success', partial: 'warning', error: 'danger', unavailable: 'secondary', unconfigured: 'secondary'};
    let checkedAt = null;
    function toggle() {
        form.querySelectorAll('[data-role]').forEach(node => { node.hidden = node.dataset.role !== role.value; });
    }
    toggle();
    form.addEventListener('input', () => {
        toggle();
        if (output.children.length) { output.replaceChildren(); checkedAt = null; message.textContent = t.changed; }
    });
    setInterval(() => {
        if (checkedAt && Date.now() - checkedAt > 300000) {
            message.textContent = t.stale;
            output.classList.add('opacity-50');
        }
    }, 15000);
    function render(results) {
        output.replaceChildren(); output.classList.remove('opacity-50');
        results.forEach(result => {
            const col = document.createElement('div'); col.className = 'col-md-6';
            const card = document.createElement('section'); card.className = 'card p-3 h-100';
            const heading = document.createElement('h2'); heading.className = 'h6'; heading.textContent = result.name;
            const status = document.createElement('span'); status.className = 'badge align-self-start text-bg-' + (colors[result.state] || 'secondary');
            status.textContent = t[result.state] || t.unavailable;
            const reason = document.createElement('p'); reason.className = 'small mt-2 mb-1'; reason.textContent = t[result.reason] || t.failure;
            const data = document.createElement('p'); data.className = 'small text-body-secondary mb-1';
            const parts = [];
            if (result.rcode) parts.push('RCODE: ' + result.rcode + ' / ' + result.expected);
            if (result.answers?.length) parts.push(result.answers.join(', '));
            if (result.certificate_expires) parts.push(t.certificateLabel + ' ' + result.certificate_expires + ' · ' + result.certificate_days + ' ' + t.days);
            data.textContent = parts.join(' · ');
            const stamp = document.createElement('small'); stamp.className = 'text-body-secondary';
            stamp.textContent = t.source + ' · ' + new Date(result.checked_at).toLocaleString() + ' · ' + result.elapsed_ms + ' ms';
            card.append(heading, status, reason, data, stamp); col.append(card); output.append(col);
        });
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const config = Object.fromEntries(new FormData(form));
        const action = event.submitter?.value || 'run';
        const buttons = [...form.querySelectorAll('button')]; buttons.forEach(b => { b.disabled = true; });
        const inputs = [...form.querySelectorAll('input, select')]; inputs.forEach(i => { i.disabled = true; });
        if (action === 'run') { checkedAt = null; output.replaceChildren(); }
        message.textContent = t.running;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 45000);
        try {
            const response = await fetch(location.pathname, {method: 'POST', signal: controller.signal,
                headers: {'Content-Type': 'application/json', 'X-Diagnostics-Token': form.dataset.token},
                body: JSON.stringify({action, config}), cache: 'no-store'});
            const body = await response.json();
            if (!response.ok) throw new Error(body.error || t.failure);
            if (action === 'save') message.textContent = t.saved;
            else { render(body.results); checkedAt = Date.now(); message.textContent = t.source; }
        } catch (error) {
            message.textContent = error.name === 'AbortError' ? t.timeout : (error instanceof SyntaxError || error instanceof TypeError ? t.failure : error.message);
        } finally {
            clearTimeout(timer); buttons.forEach(b => { b.disabled = false; }); inputs.forEach(i => { i.disabled = false; });
        }
    });
})();
