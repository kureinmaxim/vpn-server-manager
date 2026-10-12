/* Progressive enhancement: keep only the requested section visible. */
(() => {
    const page = document.querySelector('.monitoring-page');
    if (!page) return;
    const groups = {
        overview: '.monitoring-overview, #load-diagnosis',
        network: '.network-traffic, .firewall-status',
        services: '.active-services, .telegramonly-stack, .reticulum-status, .webpanels, .file-manager-status',
        security: '.security-events',
        history: '.mini-charts',
    };
    const links = [...page.querySelectorAll('.monitoring-nav a')];
    function showSection(section) {
        if (!Object.hasOwn(groups, section)) section = 'overview';
        Object.entries(groups).forEach(([name, selector]) => {
            page.querySelectorAll(selector).forEach(el => { el.hidden = name !== section; });
        });
        // Empty Bootstrap columns must not retain their width or gutters.
        page.querySelectorAll('[class*="col-"]').forEach(column => {
            const cards = [...column.querySelectorAll('.monitoring-card')];
            if (cards.length) column.hidden = cards.every(card => card.hidden);
        });
        const grid = page.querySelector('.monitoring-grid');
        if (grid) grid.hidden = section === 'overview';
        links.forEach(link => {
            if (link.hash === '#monitoring-' + section) link.setAttribute('aria-current', 'true');
            else link.removeAttribute('aria-current');
        });
        // Charts created while hidden need their new container dimensions.
        window.dispatchEvent(new Event('resize'));
    }
    links.forEach(link => link.addEventListener('click', event => {
        event.preventDefault();
        showSection(link.hash.replace('#monitoring-', ''));
    }));
    showSection(location.hash.replace('#monitoring-', ''));
})();
