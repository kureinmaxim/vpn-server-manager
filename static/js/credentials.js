/**
 * Безопасное копирование / показ паролей и очистка вставки.
 * Не вставляйте секреты в onclick="...('пароль')" — только в data-* атрибуты
 * с обычным экранированием Jinja ("{{ value }}"). Фильтр |tojson здесь нельзя:
 * браузер не парсит JSON в атрибутах, поэтому \\ и \uXXXX попадут в пароль как есть.
 */
(function (global) {
    'use strict';

    var INVISIBLE_RE = /[\u200B-\u200D\u2060\uFEFF\u00AD\u202A-\u202E\u2066-\u2069]/g;

    function sanitizeSecret(value) {
        if (value == null) return '';
        var text = String(value);
        text = text.replace(/\r\n?/g, '').replace(/\n/g, '');
        text = text.replace(INVISIBLE_RE, '');
        return text.trim();
    }

    function resolveCopyText(button, explicitText) {
        if (explicitText != null && explicitText !== '') {
            return sanitizeSecret(explicitText);
        }
        if (!button) return '';

        var fromAttr = button.getAttribute('data-copy-value');
        if (fromAttr != null && fromAttr !== '') {
            return sanitizeSecret(fromAttr);
        }

        var group = button.closest('.input-group');
        if (group) {
            var secretField = group.querySelector('[data-password]');
            if (secretField) {
                return sanitizeSecret(secretField.getAttribute('data-password'));
            }
            var copyField = group.querySelector('[data-copy-value]');
            if (copyField) {
                return sanitizeSecret(copyField.getAttribute('data-copy-value'));
            }
            var input = group.querySelector('input.secret-input, input[type="password"], input[type="text"]');
            if (input) {
                return sanitizeSecret(input.value);
            }
        }
        return '';
    }

    function flashCopied(button) {
        if (!button) return;
        var original = button.innerHTML;
        button.innerHTML = '<i class="bi bi-check-lg"></i>';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-secondary');
        setTimeout(function () {
            button.innerHTML = original;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 1200);
    }

    function fallbackCopy(text) {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try {
            return document.execCommand('copy');
        } catch (e) {
            return false;
        } finally {
            document.body.removeChild(ta);
        }
    }

    function copyToClipboard(button, textToCopy) {
        var text = resolveCopyText(button, textToCopy);
        var done = function () { flashCopied(button); };
        var fail = function (err) {
            if (fallbackCopy(text)) {
                done();
                return;
            }
            console.error('Clipboard error:', err);
        };

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done).catch(fail);
        } else if (fallbackCopy(text)) {
            done();
        } else {
            fail(new Error('clipboard unavailable'));
        }
    }

    function togglePassword(button) {
        if (!button) return;
        var group = button.closest('.input-group');
        var span = group
            ? group.querySelector('.password-field')
            : button.previousElementSibling;
        if (!span) return;

        var password = sanitizeSecret(span.getAttribute('data-password'));
        var eyeIcon = button.querySelector('i');
        var hidden = span.getAttribute('data-hidden') !== '0';

        if (hidden) {
            span.textContent = password || '';
            span.setAttribute('data-hidden', '0');
            if (eyeIcon) {
                eyeIcon.classList.remove('bi-eye');
                eyeIcon.classList.add('bi-eye-slash');
            }
        } else {
            span.textContent = '••••••••';
            span.setAttribute('data-hidden', '1');
            if (eyeIcon) {
                eyeIcon.classList.remove('bi-eye-slash');
                eyeIcon.classList.add('bi-eye');
            }
        }
    }

    function togglePasswordInput(button) {
        if (!button) return;
        var group = button.closest('.input-group');
        var input = group && group.querySelector('input.secret-input, input[type="password"], input[type="text"]');
        if (!input) return;
        var eyeIcon = button.querySelector('i');
        var show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        if (eyeIcon) {
            eyeIcon.classList.toggle('bi-eye', !show);
            eyeIcon.classList.toggle('bi-eye-slash', show);
        }
    }

    function copyPasswordInput(button) {
        copyToClipboard(button);
    }

    function bindPasteSanitize(root) {
        var scope = root || document;
        scope.querySelectorAll('input.secret-input, input[data-sanitize-paste]').forEach(function (input) {
            if (input.dataset.sanitizeBound === '1') return;
            input.dataset.sanitizeBound = '1';
            input.addEventListener('paste', function (e) {
                var clip = e.clipboardData || window.clipboardData;
                if (!clip) return;
                var raw = clip.getData('text');
                if (raw == null) return;
                var cleaned = sanitizeSecret(raw);
                if (cleaned === raw) return;
                e.preventDefault();
                var start = input.selectionStart;
                var end = input.selectionEnd;
                var value = input.value;
                input.value = value.slice(0, start) + cleaned + value.slice(end);
                var caret = start + cleaned.length;
                input.setSelectionRange(caret, caret);
                input.dispatchEvent(new Event('input', { bubbles: true }));
            });
            input.addEventListener('blur', function () {
                var cleaned = sanitizeSecret(input.value);
                if (cleaned !== input.value) {
                    input.value = cleaned;
                }
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        bindPasteSanitize(document);
    });

    global.sanitizeSecret = sanitizeSecret;
    global.copyToClipboard = copyToClipboard;
    global.togglePassword = togglePassword;
    global.togglePasswordInput = togglePasswordInput;
    global.copyPasswordInput = copyPasswordInput;
    global.bindPasteSanitize = bindPasteSanitize;
})(window);
