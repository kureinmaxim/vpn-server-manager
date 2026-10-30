/* Bootstrap owns focus trapping and Escape; keep programmatic dialogs usable. */
(() => {
    const openers = new WeakMap();
    document.addEventListener('show.bs.modal', (event) => {
        const modal = event.target;
        openers.set(modal, event.relatedTarget || document.activeElement);
        modal.querySelectorAll('[data-bs-toggle="tab"]').forEach((tab) => {
            bootstrap.Tab.getOrCreateInstance(tab);
        });
    });
    document.addEventListener('shown.bs.modal', (event) => {
        const modal = event.target;
        const input = modal.querySelector(modal.dataset.modalInitialFocus || '#pinInput, #newPinInput');
        if (input && input.getClientRects().length) input.focus();
    });
    document.addEventListener('hidden.bs.modal', (event) => {
        const opener = openers.get(event.target);
        openers.delete(event.target);
        if (!document.querySelector('.modal.show') && opener?.isConnected &&
            !opener.disabled && opener.getClientRects().length) opener.focus();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' || event.isComposing || event.repeat) return;
        if (event.target.id === 'pinInput') {
            event.preventDefault();
            const button = event.target.closest('.modal').querySelector('#modalSubmitBtn');
            if (button && !button.disabled) button.click();
        }
    });
    document.addEventListener('submit', (event) => {
        const handlers = {changePinForm: 'submitChangePin', createPinForm: 'submitCreatePin'};
        const handler = handlers[event.target.id];
        if (!handler) return;
        event.preventDefault();
        if (event.target.checkValidity() && typeof window[handler] === 'function') {
            window[handler]();
        }
    });
})();
