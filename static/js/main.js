/**
 * FoodBridge · Floating pill navigation
 * - Mobile menu toggle (Escape / outside click / link click closes it)
 * - Scrolled state and hide-on-scroll-down, reveal-on-scroll-up
 * - Native scroll spy for in-page section links (replaces Bootstrap ScrollSpy)
 */
(function () {
    'use strict';

    function initNav() {
        const shell = document.getElementById('mainNav');
        if (!shell) return;

        const nav = shell.querySelector('.wn-nav');
        const toggle = shell.querySelector('.wn-nav__toggle');
        const links = Array.from(shell.querySelectorAll('.wn-nav__links a'));

        const isOpen = () => Boolean(nav && nav.classList.contains('is-open'));
        const setOpen = (open) => {
            if (!nav || !toggle) return;
            nav.classList.toggle('is-open', open);
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
            if (open) shell.classList.remove('is-hidden');
        };

        if (toggle) toggle.addEventListener('click', () => setOpen(!isOpen()));
        links.forEach((link) => link.addEventListener('click', () => setOpen(false)));
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && isOpen()) {
                setOpen(false);
                if (toggle) toggle.focus();
            }
        });
        document.addEventListener('click', (event) => {
            if (isOpen() && !shell.contains(event.target)) setOpen(false);
        });

        // Scrolled state + hide on scroll down
        let lastY = window.scrollY;
        let ticking = false;
        const update = () => {
            const y = window.scrollY;
            shell.classList.toggle('scrolled', y > 24);
            const delta = y - lastY;
            if (Math.abs(delta) > 6) {
                const hide = delta > 0 && y > 480 && !isOpen() && !shell.matches(':focus-within');
                shell.classList.toggle('is-hidden', hide);
                lastY = y;
            }
            ticking = false;
        };
        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(update);
                ticking = true;
            }
        }, { passive: true });
        update();

        // Scroll spy (only links pointing to sections on the current page)
        if (!('IntersectionObserver' in window)) return;
        const spyLinks = links.filter((a) => a.hash && a.pathname === window.location.pathname);
        const byId = new Map();
        spyLinks.forEach((a) => {
            const id = decodeURIComponent(a.hash.slice(1));
            if (document.getElementById(id)) byId.set(id, a);
        });
        if (!byId.size) return;

        const spy = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                spyLinks.forEach((a) => a.classList.remove('active'));
                const link = byId.get(entry.target.id);
                if (link) link.classList.add('active');
            });
        }, { rootMargin: '-45% 0px -50% 0px' });

        byId.forEach((_link, id) => spy.observe(document.getElementById(id)));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNav);
    } else {
        initNav();
    }
})();
