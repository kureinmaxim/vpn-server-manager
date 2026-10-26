const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/http_security.js', 'utf8');

function environment(fetchImpl) {
    const handlers = {};
    const forms = [];
    class Form {
        constructor(action = 'http://localhost/save', method = 'post') {
            this.action = action; this.method = method; this.fields = [];
        }
        querySelector() { return this.fields.find(field => field.name === 'csrf_token'); }
        append(field) { this.fields.push(field); }
    }
    const context = {Request, Headers, URL, AbortController, TextDecoder, queueMicrotask,
        HTMLFormElement: Form, location: {origin: 'http://localhost', href: 'http://localhost/'},
        document: {
            querySelector: () => ({content: 'csrf-fixture'}),
            querySelectorAll: () => forms,
            createElement: () => ({}),
            addEventListener: (name, callback) => handlers[name] = callback,
        }};
    context.window = {fetch: fetchImpl};
    context.fetch = (...args) => context.window.fetch(...args);
    vm.runInNewContext(source, context);
    return {...context, handlers, forms, Form};
}

test('token goes only to same-origin mutations, preserving explicit tokens', async () => {
    const seen = [];
    const env = environment(request => { seen.push(request); return Promise.resolve(new Response('ok')); });
    await env.window.fetch('http://localhost/save', {method: 'POST'});
    await env.window.fetch('http://localhost/read');
    await env.window.fetch('https://example.com/save', {method: 'POST'});
    await env.window.fetch('http://localhost/save', {method: 'POST', headers: {'X-CSRF-Token': 'explicit'}});
    assert.deepEqual(seen.map(r => r.headers.get('X-CSRF-Token')), ['csrf-fixture', null, null, 'explicit']);
});

test('regular and dynamically created forms receive tokens', () => {
    const env = environment(() => {});
    const local = new env.Form(), external = new env.Form('https://example.com/');
    env.forms.push(local, external);
    env.handlers.DOMContentLoaded();
    assert.equal(local.fields[0].value, 'csrf-fixture');
    assert.equal(external.fields.length, 0);
    const dynamic = new env.Form();
    env.handlers.submit({target: dynamic});
    assert.equal(dynamic.fields[0].value, 'csrf-fixture');
    const data = new FormData();
    env.handlers.formdata({target: dynamic, formData: data});
    assert.equal(data.get('csrf_token'), 'csrf-fixture');
});

test('POST SSE handles fragmented UTF-8 and never reconnects', async () => {
    let calls = 0;
    const bytes = new TextEncoder().encode('data: {"step":"готово"}\r\n\r\n');
    const env = environment(request => {
        calls++;
        assert.equal(request.method, 'POST');
        assert.equal(request.headers.get('X-CSRF-Token'), 'csrf-fixture');
        return Promise.resolve(new Response(new ReadableStream({start(controller) {
            for (const byte of bytes) controller.enqueue(Uint8Array.of(byte));
            controller.close();
        }})));
    });
    const values = [];
    await new Promise((resolve, reject) => {
        const stream = new env.window.PostEventSource('http://localhost/install');
        stream.onmessage = event => values.push(JSON.parse(event.data).step);
        stream.onerror = () => { try { assert.deepEqual(values, ['готово']); resolve(); } catch (e) { reject(e); } };
    });
    assert.equal(calls, 1);
});
