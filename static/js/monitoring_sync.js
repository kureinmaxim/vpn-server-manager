/* Exchange with the server, shown live: every monitoring request is a step with its state,
   time and size; the bar and the estimate come from this server's previous load. After the
   first load the panel shrinks to one line: when the data was updated and what is polling now. */
(() => {
    const root = document.getElementById('mon-sync');
    if (!root) return;
    const serverId = root.dataset.server;
    const t = JSON.parse(root.dataset.i18n || '{}');
    const STEPS = JSON.parse(root.dataset.steps || '[]');  // [[endpoint, label], ...]
    const labels = Object.fromEntries(STEPS);
    // Measured on a slow 1-vCPU VPS; replaced by this server's own timings after the first load.
    const DEFAULT_MS = {'check-installed': 3000, 'metrics-history': 7000, 'check-tools': 7000,
        'network-stats': 10000, 'firewall-stats': 8000, 'services-stats': 8000,
        'reticulum-status': 8000, 'webpanels': 6000, 'security-events': 12000};
    const storeKey = 'mon-sync-' + serverId;
    let past = {};
    try { past = JSON.parse(localStorage.getItem(storeKey) || '{}') || {}; } catch (e) { past = {}; }

    const el = sel => root.querySelector(sel);
    const steps = {};          // endpoint -> {state, start, ms, bytes, error}
    const inflight = new Set();
    const started = performance.now();
    let finished = 0, lastUpdate = null, initialDone = false, ticker = null;

    const fmtSec = ms => (ms / 1000).toFixed(ms < 10000 ? 1 : 0) + ' ' + t.sec;
    const fmtSize = bytes => bytes < 1024 ? bytes + ' B' : (bytes / 1024).toFixed(bytes < 10240 ? 1 : 0) + ' KB';
    const expected = key => (past.steps && past.steps[key]) || DEFAULT_MS[key] || 6000;

    function renderSteps() {
        const list = el('.mon-sync-steps');
        list.replaceChildren(...STEPS.map(([key, label]) => {
            const step = steps[key] || {state: 'wait'};
            const chip = document.createElement('span');
            chip.className = 'mon-step mon-step-' + step.state;
            const icon = document.createElement('i');
            icon.setAttribute('aria-hidden', 'true');
            icon.className = step.state === 'ok' ? 'bi bi-check2' : step.state === 'err' ? 'bi bi-x-lg'
                : step.state === 'run' ? 'mon-step-spin' : 'bi bi-circle';
            const text = document.createElement('span');
            text.textContent = label + (step.state === 'ok' || step.state === 'err' ? ' · ' + fmtSec(step.ms) : '');
            chip.append(icon, text);
            chip.title = step.state === 'err' ? (step.error || t.failed)
                : step.state === 'ok' ? fmtSize(step.bytes) : step.state === 'run' ? t.running : t.waiting;
            return chip;
        }));
    }

    function renderHead() {
        const now = performance.now();
        const elapsed = now - started;
        const total = STEPS.length;
        const bytes = Object.values(steps).reduce((sum, step) => sum + (step.bytes || 0), 0);
        const errors = Object.values(steps).filter(step => step.state === 'err').length;
        const weight = key => expected(key);
        const all = STEPS.reduce((sum, [key]) => sum + weight(key), 0);
        const done = STEPS.reduce((sum, [key]) => sum + (['ok', 'err'].includes((steps[key] || {}).state) ? weight(key) : 0), 0);
        const lastTotal = past.total || 30000;
        // Bar: finished work, moving smoothly with time between answers but never claiming the end.
        const fraction = initialDone ? 1 : Math.min(0.96, Math.max(done / all, elapsed / lastTotal * 0.9));
        el('.mon-sync-fill').style.width = (fraction * 100).toFixed(1) + '%';
        el('.mon-sync-count').textContent = t.count.replace('{done}', finished).replace('{total}', total);
        el('.mon-sync-time').textContent = fmtSec(elapsed);
        el('.mon-sync-size').textContent = fmtSize(bytes) + (past.bytes && !initialDone ? ' / ~' + fmtSize(past.bytes) : '');
        const eta = el('.mon-sync-eta');
        if (initialDone) {
            eta.textContent = errors ? t.doneErrors.replace('{count}', errors) : '';
        } else {
            const left = lastTotal - elapsed;
            eta.textContent = left > 1500 ? t.left.replace('{time}', fmtSec(left)) : t.slower;
        }
        root.classList.toggle('has-errors', errors > 0);
    }

    function renderLive() {
        const live = el('.mon-sync-live-text');
        if (inflight.size) {
            live.textContent = t.polling.replace('{list}', [...inflight].map(key => labels[key]).join(', '));
        } else if (lastUpdate) {
            const ago = Math.round((Date.now() - lastUpdate) / 1000);
            live.textContent = ago < 5 ? t.justNow : t.ago.replace('{time}', ago + ' ' + t.sec);
        }
        root.classList.toggle('is-polling', inflight.size > 0);
    }

    function finishInitial() {
        initialDone = true;
        try {
            const timings = Object.fromEntries(Object.entries(steps).filter(([, s]) => s.state === 'ok').map(([k, s]) => [k, Math.round(s.ms)]));
            const bytes = Object.values(steps).reduce((sum, step) => sum + (step.bytes || 0), 0);
            localStorage.setItem(storeKey, JSON.stringify({total: Math.round(performance.now() - started), bytes, steps: timings}));
        } catch (e) { /* private window: estimates just stay default */ }
        root.classList.add('is-done');
        el('.mon-sync-title').textContent = t.done.replace('{time}', fmtSec(performance.now() - started));
        renderHead();
        renderSteps();
        // Without errors the details fold away after a moment; with errors they stay visible.
        if (!root.classList.contains('has-errors')) setTimeout(() => root.classList.add('is-compact'), 2500);
        el('.mon-sync-toggle').hidden = false;
    }

    function settle(key, state, bytes, error) {
        inflight.delete(key);
        lastUpdate = Date.now();
        const step = steps[key];
        if (!initialDone && step && step.state === 'run') {
            step.state = state;
            step.ms = performance.now() - step.start;
            step.bytes = bytes;
            step.error = error;
            finished += 1;
            renderSteps();
            renderHead();
            if (finished >= STEPS.length) finishInitial();
        } else if (initialDone && step) {
            step.state = state; step.error = error;
            if (state === 'err') root.classList.add('has-errors');
            renderSteps();
        }
        renderLive();
    }

    function track(key, request) {
        inflight.add(key);
        if (!initialDone && steps[key] && steps[key].state === 'err') {
            delete steps[key];  // retry (e.g. «Повторить» after a failed installation check)
            finished -= 1;
        }
        if (!initialDone && !steps[key]) {
            steps[key] = {state: 'run', start: performance.now(), bytes: 0};
            renderSteps();
        }
        renderLive();
        return request.then(response => {
            response.clone().text().then(body => {
                let ok = response.ok, error = '';
                try {
                    const data = JSON.parse(body);
                    if (data && data.success === false) { ok = false; error = data.error || ''; }
                    if (key === 'check-installed' && data && data.installed === false) {
                        root.hidden = true;  // the installation panel takes over
                    }
                } catch (e) { /* streamed or non-JSON answer: HTTP status decides */ }
                if (!response.ok && !error) error = 'HTTP ' + response.status;
                settle(key, ok ? 'ok' : 'err', body.length, error);
            }).catch(() => settle(key, 'err', 0, t.failed));
            return response;
        }, failure => {
            settle(key, 'err', 0, t.failed);
            throw failure;
        });
    }

    const nativeFetch = window.fetch.bind(window);
    const prefix = '/api/monitoring/' + serverId + '/';
    window.fetch = function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        const path = url.startsWith(prefix) ? url.slice(prefix.length).split(/[?/]/)[0] : '';
        const method = ((init && init.method) || 'GET').toUpperCase();
        if (method !== 'GET' || !labels[path]) return nativeFetch(input, init);
        return track(path, nativeFetch(input, init));
    };

    el('.mon-sync-toggle').addEventListener('click', () => root.classList.toggle('is-compact'));
    root.hidden = false;
    renderSteps();
    renderHead();
    ticker = setInterval(() => {
        if (!initialDone) renderHead();
        renderLive();
        if (root.hidden) clearInterval(ticker);
    }, 500);
})();
