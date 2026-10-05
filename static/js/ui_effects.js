/**
 * FoodBridge UI Modern Effects
 * - 3D Card Tilt with dynamic specular sheen
 * - Animated Counter Micro-interactions
 * - Ambient Mouse Glow
 * - Mobile Drawer & App Navigation ergonomics
 * - PWA Service Worker Registration
 */

(function () {
    'use strict';

    // ── 1. 3D CARD TILT WITH SPECULAR GLARE ──
    function initCardTilt() {
        // Only run on devices that support hover / fine pointers
        const isTouch = window.matchMedia('(pointer: coarse)').matches;
        const tiltCards = document.querySelectorAll('.tilt-card, [data-tilt]');

        tiltCards.forEach((card) => {
            // Create specular glare overlay if not present
            let glare = card.querySelector('.tilt-glare');
            if (!glare) {
                glare = document.createElement('div');
                glare.className = 'tilt-glare';
                card.appendChild(glare);
            }

            if (isTouch) return; // Skip continuous tilt calculations on touch for performance

            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const centerX = rect.width / 2;
                const centerY = rect.height / 2;

                const rotateX = ((y - centerY) / centerY) * -9; // Max 9 deg
                const rotateY = ((x - centerX) / centerX) * 9;

                card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px)`;

                // Update glare position
                const glareX = (x / rect.width) * 100;
                const glareY = (y / rect.height) * 100;
                glare.style.background = `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 65%)`;
                glare.style.opacity = '1';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
                glare.style.opacity = '0';
            });
        });
    }

    // ── 2. ANIMATED NUMBER COUNTERS ──
    function initCounters() {
        const counters = document.querySelectorAll('[data-counter]');
        if (!counters.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const target = parseInt(el.getAttribute('data-counter'), 10);
                    const suffix = el.getAttribute('data-suffix') || '';
                    const prefix = el.getAttribute('data-prefix') || '';
                    const duration = 1800; // ms
                    const startTime = performance.now();

                    function updateCount(currentTime) {
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        // Ease out quart
                        const easeProgress = 1 - Math.pow(1 - progress, 4);
                        const current = Math.floor(easeProgress * target);

                        el.textContent = `${prefix}${current.toLocaleString()}${suffix}`;

                        if (progress < 1) {
                            requestAnimationFrame(updateCount);
                        } else {
                            el.textContent = `${prefix}${target.toLocaleString()}${suffix}`;
                        }
                    }

                    requestAnimationFrame(updateCount);
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.2 });

        counters.forEach((c) => observer.observe(c));
    }

    // ── 3. AMBIENT CURSOR GLOW (DESKTOP) ──
    function initCursorGlow() {
        if (window.matchMedia('(pointer: coarse)').matches) return;

        const glowEl = document.createElement('div');
        glowEl.className = 'cursor-ambient-glow';
        document.body.appendChild(glowEl);

        let mouseX = -500, mouseY = -500;
        let glowX = -500, glowY = -500;

        window.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        }, { passive: true });

        function renderGlow() {
            glowX += (mouseX - glowX) * 0.12;
            glowY += (mouseY - glowY) * 0.12;
            glowEl.style.transform = `translate3d(${glowX}px, ${glowY}px, 0)`;
            requestAnimationFrame(renderGlow);
        }

        renderGlow();
    }

    // ── 4. MOBILE DRAWER & BOTTOM SHEET ──
    function initMobileDrawers() {
        const drawerTriggers = document.querySelectorAll('[data-open-drawer]');
        const closeTriggers = document.querySelectorAll('[data-close-drawer]');

        drawerTriggers.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const drawerId = btn.getAttribute('data-open-drawer');
                const drawer = document.getElementById(drawerId);
                if (drawer) {
                    drawer.classList.add('active');
                    document.body.classList.add('drawer-open');
                }
            });
        });

        closeTriggers.forEach((btn) => {
            btn.addEventListener('click', () => {
                const activeDrawers = document.querySelectorAll('.mobile-sheet.active');
                activeDrawers.forEach((d) => d.classList.remove('active'));
                document.body.classList.remove('drawer-open');
            });
        });

        // Close on backdrop click
        document.querySelectorAll('.mobile-sheet-backdrop').forEach((backdrop) => {
            backdrop.addEventListener('click', () => {
                const sheet = backdrop.closest('.mobile-sheet');
                if (sheet) sheet.classList.remove('active');
                document.body.classList.remove('drawer-open');
            });
        });
    }

    // ── 5. PWA SERVICE WORKER REGISTRATION ──
    function registerServiceWorker() {
        if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
            navigator.serviceWorker.register('/static/js/sw.js').catch(() => {
                // Silently ignore registration failure in non-root or restrictive contexts
            });
        }
    }

    // Initialize all
    function init() {
        initCardTilt();
        initCounters();
        initCursorGlow();
        initMobileDrawers();
        registerServiceWorker();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
