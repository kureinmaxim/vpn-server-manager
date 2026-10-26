/* Same-origin fetches and regular forms share the server-generated CSRF token. */
(function () {
    const token = document.querySelector('meta[name="csrf-token"]').content;
    const originalFetch = window.fetch.bind(window);
    window.fetch = function (input, options = {}) {
        const request = new Request(input, options);
        if (new URL(request.url).origin === location.origin && !['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
            const headers = new Headers(request.headers);
            if (!headers.has('X-CSRF-Token')) headers.set('X-CSRF-Token', token);
            return originalFetch(new Request(request, {headers}));
        }
        return originalFetch(request);
    };
    function protect(form) {
        if ((form.method || 'get').toLowerCase() !== 'post' || new URL(form.action || location.href).origin !== location.origin) return;
        if (!form.querySelector('[name="csrf_token"]')) {
            const field = document.createElement('input');
            field.type = 'hidden'; field.name = 'csrf_token'; field.value = token;
            form.append(field);
        }
    }
    document.addEventListener('DOMContentLoaded', () => document.querySelectorAll('form').forEach(protect));
    document.addEventListener('submit', event => protect(event.target), true);
    document.addEventListener('formdata', event => {
        const form = event.target;
        if (form instanceof HTMLFormElement && new URL(form.action || location.href).origin === location.origin)
            event.formData.set('csrf_token', token);
    });
})();

/* A POST stream, deliberately without EventSource's automatic reconnect/re-execution. */
window.PostEventSource = class {
    constructor(url) {
        this.controller = new AbortController();
        this.closed = false;
        queueMicrotask(() => this.read(url));
    }
    close() { this.closed = true; this.controller.abort(); }
    async read(url) {
        try {
            const response = await fetch(url, {method: 'POST', signal: this.controller.signal});
            if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (!this.closed) {
                const {value, done} = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, {stream: true});
                buffer = buffer.replace(/\r\n/g, '\n');
                let boundary;
                while ((boundary = buffer.indexOf('\n\n')) >= 0 && !this.closed) {
                    const block = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
                    const data = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
                    if (data && this.onmessage) this.onmessage({data});
                }
            }
            if (!this.closed && this.onerror) this.onerror(new Error('Stream ended'));
        } catch (error) { if (!this.closed && this.onerror) this.onerror(error); }
    }
};
