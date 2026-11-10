/* Progressive enhancement: keep only the requested section visible. */
(() => {
    const page = document.querySelector('.monitoring-page');
    if (!page) return;
    const sections = [...page.querySelectorAll('[data-mon-section]')];
    const links = [...page.querySelectorAll('a[href^="#monitoring-"]')];
    const names = sections.map(section => section.dataset.monSection);
    function showSection(name, focus) {
        if (!names.includes(name)) name = 'overview';
        sections.forEach(section => { section.hidden = section.dataset.monSection !== name; });
        links.forEach(link => {
            if (!link.closest('.monitoring-nav')) return;
            if (link.hash === '#monitoring-' + name) link.setAttribute('aria-current', 'true');
            else link.removeAttribute('aria-current');
        });
        if (focus) history.replaceState(null, '', '#monitoring-' + name);
        // Charts created while hidden need their new container dimensions.
        window.dispatchEvent(new Event('resize'));
    }
    links.forEach(link => link.addEventListener('click', event => {
        event.preventDefault();
        showSection(link.hash.replace('#monitoring-', ''), true);
    }));
    window.addEventListener('hashchange', () => showSection(location.hash.replace('#monitoring-', '')));
    showSection(location.hash.replace('#monitoring-', ''));
})();
