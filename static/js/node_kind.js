// Server form: VPS-only fields (provider, payment, hoster, VPN checks) hide for NAS and PC.
// Hidden fields keep their values and are still submitted, so switching back loses nothing.
(function () {
    const select = document.getElementById('kind');
    if (!select) return;
    function apply() {
        document.querySelectorAll('[data-node-kinds]').forEach(block => {
            block.hidden = !block.dataset.nodeKinds.split(' ').includes(select.value);
        });
    }
    select.addEventListener('change', apply);
    apply();
})();
