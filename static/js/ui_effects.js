/**
 * FoodBridge · Wanantara UI Effects
 * - Framer-style scroll reveals with stagger
 * - Accessible FAQ accordions
 * - Eased metric counters (integer and decimal)
 * - 3D card tilt with specular glare, cursor spotlight, magnetic buttons
 * - Hero parallax, ambient cursor glow, toast auto-dismiss
 * - Mobile drawers and PWA service worker registration
 */
(function () {
    'use strict';

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const coarsePointer = window.matchMedia('(pointer: coarse)').matches;

    // ── 1. SCROLL REVEALS ──
    function initReveals() {
        const items = document.querySelectorAll('.reveal');
        if (!items.length) return;

        document.querySelectorAll('[data-reveal-stagger]').forEach((group) => {
            const step = parseInt(group.getAttribute('data-reveal-stagger'), 10) || 90;
            group.querySelectorAll(':scope > .reveal').forEach((child, index) => {
                child.style.transitionDelay = `${index * step}ms`;
            });
        });

        const show = (el) => {
            el.classList.add('visible');
            if (el.style.transitionDelay) {
                // Clear the stagger delay once revealed so hover/tilt stays instant.
                el.addEventListener('transitionend', () => { el.style.transitionDelay = ''; }, { once: true });
            }
        };

        if (reduceMotion || !('IntersectionObserver' in window)) {
            items.forEach(show);
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                show(entry.target);
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -6% 0px' });

        items.forEach((el) => observer.observe(el));
    }

    // ── 2. ACCORDIONS ──
    function initAccordions() {
        document.querySelectorAll('[data-accordion]').forEach((accordion) => {
            const single = accordion.getAttribute('data-accordion') !== 'multi';
            const items = Array.from(accordion.querySelectorAll('.wn-accordion__item'));

            const setState = (item, open) => {
                const trigger = item.querySelector('.wn-accordion__trigger');
                const panel = item.querySelector('.wn-accordion__panel');
                item.classList.toggle('is-open', open);
                if (trigger) trigger.setAttribute('aria-expanded', String(open));
                if (panel) {
                    if (open) panel.removeAttribute('inert');
                    else panel.setAttribute('inert', '');
                }
            };

            items.forEach((item) => {
                setState(item, item.classList.contains('is-open'));
                const trigger = item.querySelector('.wn-accordion__trigger');
                if (!trigger) return;
                trigger.addEventListener('click', () => {
                    const willOpen = !item.classList.contains('is-open');
                    if (single && willOpen) {
                        items.forEach((other) => { if (other !== item) setState(other, false); });
                    }
                    setState(item, willOpen);
                });
            });
        });
    }

    // ── 3. METRIC COUNTERS ──
    function initCounters() {
        const counters = document.querySelectorAll('[data-counter]');
        if (!counters.length) return;

        const easeOutExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));

        const run = (el) => {
            const raw = el.getAttribute('data-counter');
            const target = parseFloat(raw);
            if (!Number.isFinite(target)) return;

            const decimalsAttr = el.getAttribute('data-decimals');
            const decimals = decimalsAttr !== null
                ? Math.max(0, parseInt(decimalsAttr, 10) || 0)
                : (String(raw).split('.')[1] || '').length;
            const prefix = el.getAttribute('data-prefix') || '';
            const suffix = el.getAttribute('data-suffix') || '';
            const duration = parseInt(el.getAttribute('data-duration'), 10) || 2000;
            const format = (value) => value.toLocaleString(undefined, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals,
            });
            const render = (value) => { el.textContent = `${prefix}${format(value)}${suffix}`; };

            if (reduceMotion) { render(target); return; }

            const start = performance.now();
            const tick = (now) => {
                const progress = Math.min((now - start) / duration, 1);
                const current = target * easeOutExpo(progress);
                render(decimals ? current : Math.round(current));
                if (progress < 1) requestAnimationFrame(tick);
                else render(target);
            };
            requestAnimationFrame(tick);
        };

        if (!('IntersectionObserver' in window)) { counters.forEach(run); return; }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                run(entry.target);
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.35 });

        counters.forEach((el) => observer.observe(el));
    }

    // ── 4. 3D CARD TILT WITH SPECULAR GLARE ──
    function initCardTilt() {
        const cards = document.querySelectorAll('.tilt-card, [data-tilt]');
        cards.forEach((card) => {
            let glare = card.querySelector(':scope > .tilt-glare');
            if (!glare) {
                glare = document.createElement('div');
                glare.className = 'tilt-glare';
                card.appendChild(glare);
            }
            if (coarsePointer || reduceMotion) return;

            let frame = null;
            card.addEventListener('mousemove', (event) => {
                if (frame) cancelAnimationFrame(frame);
                frame = requestAnimationFrame(() => {
                    const rect = card.getBoundingClientRect();
                    const x = event.clientX - rect.left;
                    const y = event.clientY - rect.top;
                    const rotateX = ((y - rect.height / 2) / (rect.height / 2)) * -6;
                    const rotateY = ((x - rect.width / 2) / (rect.width / 2)) * 6;
                    card.style.transform = `perspective(1100px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px)`;
                    glare.style.background = `radial-gradient(circle at ${(x / rect.width) * 100}% ${(y / rect.height) * 100}%, rgba(255, 236, 179, 0.16) 0%, rgba(255, 255, 255, 0) 60%)`;
                    glare.style.opacity = '1';
                });
            });
            card.addEventListener('mouseleave', () => {
                if (frame) cancelAnimationFrame(frame);
                card.style.transform = '';
                glare.style.opacity = '0';
            });
        });
    }

    // ── 5. CURSOR SPOTLIGHT ──
    function initSpotlights() {
        if (coarsePointer) return;
        document.querySelectorAll('.wn-spotlight').forEach((el) => {
            el.addEventListener('mousemove', (event) => {
                const rect = el.getBoundingClientRect();
                el.style.setProperty('--mx', `${event.clientX - rect.left}px`);
                el.style.setProperty('--my', `${event.clientY - rect.top}px`);
            });
        });
    }

    // ── 6. MAGNETIC BUTTONS ──
    function initMagnetic() {
        if (coarsePointer || reduceMotion) return;
        document.querySelectorAll('[data-magnetic]').forEach((el) => {
            el.addEventListener('mousemove', (event) => {
                const rect = el.getBoundingClientRect();
                const dx = event.clientX - (rect.left + rect.width / 2);
                const dy = event.clientY - (rect.top + rect.height / 2);
                const x = Math.max(-10, Math.min(10, dx * 0.22));
                const y = Math.max(-8, Math.min(8, dy * 0.3));
                el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
            });
            el.addEventListener('mouseleave', () => { el.style.transform = ''; });
        });
    }

    // ── 7. HERO PARALLAX ──
    function initParallax() {
        if (reduceMotion) return;
        const els = Array.from(document.querySelectorAll('[data-parallax]'));
        if (!els.length) return;

        let ticking = false;
        const update = () => {
            const y = window.scrollY;
            const limit = window.innerHeight * 1.2;
            els.forEach((el) => {
                if (y > limit) return;
                const speed = parseFloat(el.getAttribute('data-parallax')) || 0.2;
                el.style.transform = `translate3d(0, ${(y * speed).toFixed(1)}px, 0)`;
                if (el.hasAttribute('data-parallax-fade')) {
                    el.style.opacity = String(Math.max(0, 1 - y / (window.innerHeight * 0.85)));
                }
            });
            ticking = false;
        };
        window.addEventListener('scroll', () => {
            if (!ticking) { requestAnimationFrame(update); ticking = true; }
        }, { passive: true });
        update();
    }

    // ── 8. AMBIENT CURSOR GLOW (DESKTOP) ──
    function initCursorGlow() {
        if (coarsePointer || reduceMotion) return;

        const glowEl = document.createElement('div');
        glowEl.className = 'cursor-ambient-glow';
        glowEl.setAttribute('aria-hidden', 'true');
        document.body.appendChild(glowEl);

        let mouseX = -500;
        let mouseY = -500;
        let glowX = -500;
        let glowY = -500;

        window.addEventListener('mousemove', (event) => {
            mouseX = event.clientX;
            mouseY = event.clientY;
        }, { passive: true });

        const render = () => {
            glowX += (mouseX - glowX) * 0.12;
            glowY += (mouseY - glowY) * 0.12;
            glowEl.style.transform = `translate3d(${glowX}px, ${glowY}px, 0)`;
            requestAnimationFrame(render);
        };
        render();
    }

    // ── 9. TOAST AUTO-DISMISS ──
    function initToasts() {
        document.querySelectorAll('[data-autodismiss]').forEach((el) => {
            const delay = parseInt(el.getAttribute('data-autodismiss'), 10) || 6000;
            window.setTimeout(() => {
                if (!document.body.contains(el)) return;
                if (window.bootstrap && window.bootstrap.Alert) {
                    window.bootstrap.Alert.getOrCreateInstance(el).close();
                } else {
                    el.remove();
                }
            }, delay);
        });
    }

    // ── 10. MOBILE DRAWERS & BOTTOM SHEETS ──
    function initMobileDrawers() {
        document.querySelectorAll('[data-open-drawer]').forEach((btn) => {
            btn.addEventListener('click', (event) => {
                event.preventDefault();
                const drawer = document.getElementById(btn.getAttribute('data-open-drawer'));
                if (drawer) {
                    drawer.classList.add('active');
                    document.body.classList.add('drawer-open');
                }
            });
        });

        const closeAll = () => {
            document.querySelectorAll('.mobile-sheet.active').forEach((d) => d.classList.remove('active'));
            document.body.classList.remove('drawer-open');
        };
        document.querySelectorAll('[data-close-drawer]').forEach((btn) => btn.addEventListener('click', closeAll));
        document.querySelectorAll('.mobile-sheet-backdrop').forEach((backdrop) => backdrop.addEventListener('click', closeAll));
    }

    // ── 11. PWA SERVICE WORKER ──
    function registerServiceWorker() {
        if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
            navigator.serviceWorker.register('/static/js/sw.js').catch(() => {
                // Ignore registration failures in restrictive contexts.
            });
        }
    }

    function init() {
        initReveals();
        initAccordions();
        initCounters();
        initCardTilt();
        initSpotlights();
        initMagnetic();
        initParallax();
        initCursorGlow();
        initToasts();
        initMobileDrawers();
        registerServiceWorker();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
