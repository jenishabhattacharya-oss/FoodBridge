/**
 * SharePlate hero — doodle kitchen tapestry
 * Built with Three.js (r128)
 *
 * A seamless, hand-drawn pattern of kitchen doodles (tomatoes, bread, leaves,
 * carrots, bowls, cutlery, wheat, sparkles) printed like gold ink on two
 * cloth planes at different depths. The cloths ripple slowly and the pattern
 * drifts, reading as a crafted textile — no glowing nodes, no stock 3D fruit.
 */

(function () {
    'use strict';

    const canvas = document.getElementById('hero3d-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    let scene, camera, renderer, clock;
    const layers = [];

    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let windowHalfX = window.innerWidth / 2;
    let windowHalfY = window.innerHeight / 2;
    let animationFrameId = null;
    let isVisible = true;

    const isMobile = window.innerWidth < 768;

    const FOG_COLOR = 0x07120a; // matches --bg-forest-900

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    /* ---------- Doodle stroke helpers ---------- */

    // A circle drawn with a little hand wobble
    function wobbleCircle(ctx, cx, cy, r, segments) {
        ctx.beginPath();
        for (let i = 0; i <= segments; i++) {
            const a = (i / segments) * Math.PI * 2;
            const rr = r * (1 + Math.sin(a * 3 + cx) * 0.035 + Math.sin(a * 5 + cy) * 0.02);
            const x = cx + Math.cos(a) * rr;
            const y = cy + Math.sin(a) * rr;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.stroke();
    }

    /* ---------- Doodle library (drawn around 0,0, roughly ±s) ---------- */

    const DOODLES = [
        // Tomato
        function (ctx, s) {
            wobbleCircle(ctx, 0, s * 0.12, s * 0.72, 26);
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.62);
            ctx.lineTo(0, -s * 0.92);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.84);
            ctx.lineTo(s * 0.3, -s * 0.98);
            ctx.moveTo(0, -s * 0.84);
            ctx.lineTo(-s * 0.3, -s * 0.98);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(0, s * 0.16, s * 0.38, Math.PI * 0.25, Math.PI * 0.85);
            ctx.stroke();
        },

        // Bread loaf with score marks
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(-s * 0.85, s * 0.55);
            ctx.quadraticCurveTo(-s * 0.95, -s * 0.1, -s * 0.5, -s * 0.45);
            ctx.quadraticCurveTo(0, -s * 0.82, s * 0.5, -s * 0.45);
            ctx.quadraticCurveTo(s * 0.95, -s * 0.1, s * 0.85, s * 0.55);
            ctx.closePath();
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-s * 0.35, -s * 0.5);
            ctx.lineTo(-s * 0.15, -s * 0.15);
            ctx.moveTo(0, -s * 0.56);
            ctx.lineTo(s * 0.2, -s * 0.21);
            ctx.moveTo(s * 0.35, -s * 0.5);
            ctx.lineTo(s * 0.55, -s * 0.15);
            ctx.stroke();
        },

        // Leaf with veins
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.9);
            ctx.bezierCurveTo(s * 0.9, -s * 0.4, s * 0.7, s * 0.6, 0, s * 0.9);
            ctx.bezierCurveTo(-s * 0.7, s * 0.6, -s * 0.9, -s * 0.4, 0, -s * 0.9);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.7);
            ctx.lineTo(0, s * 0.75);
            ctx.stroke();
            ctx.beginPath();
            for (let i = 1; i <= 3; i++) {
                const y = -s * 0.6 + i * s * 0.38;
                ctx.moveTo(0, y);
                ctx.lineTo(s * 0.32, y + s * 0.18);
                ctx.moveTo(0, y);
                ctx.lineTo(-s * 0.32, y + s * 0.18);
            }
            ctx.stroke();
        },

        // Carrot with fronds
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(-s * 0.45, -s * 0.45);
            ctx.lineTo(s * 0.45, -s * 0.45);
            ctx.quadraticCurveTo(s * 0.32, s * 0.4, 0, s * 0.92);
            ctx.quadraticCurveTo(-s * 0.32, s * 0.4, -s * 0.45, -s * 0.45);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-s * 0.28, -s * 0.15);
            ctx.lineTo(-s * 0.05, -s * 0.05);
            ctx.moveTo(-s * 0.18, s * 0.25);
            ctx.lineTo(s * 0.02, s * 0.33);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-s * 0.18, -s * 0.45);
            ctx.quadraticCurveTo(-s * 0.3, -s * 0.8, -s * 0.5, -s * 0.9);
            ctx.moveTo(0, -s * 0.45);
            ctx.quadraticCurveTo(0, -s * 0.8, 0, -s * 1.0);
            ctx.moveTo(s * 0.18, -s * 0.45);
            ctx.quadraticCurveTo(s * 0.3, -s * 0.8, s * 0.5, -s * 0.9);
            ctx.stroke();
        },

        // Apple
        function (ctx, s) {
            wobbleCircle(ctx, 0, s * 0.15, s * 0.68, 24);
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.5);
            ctx.quadraticCurveTo(s * 0.08, -s * 0.85, s * 0.24, -s * 0.95);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(s * 0.22, -s * 0.7);
            ctx.quadraticCurveTo(s * 0.62, -s * 0.82, s * 0.52, -s * 0.5);
            ctx.quadraticCurveTo(s * 0.32, -s * 0.52, s * 0.22, -s * 0.7);
            ctx.stroke();
        },

        // Bowl with steam curls
        function (ctx, s) {
            ctx.beginPath();
            ctx.arc(0, -s * 0.05, s * 0.68, 0, Math.PI);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-s * 0.28, s * 0.68);
            ctx.lineTo(s * 0.28, s * 0.68);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-s * 0.22, -s * 0.35);
            ctx.bezierCurveTo(-s * 0.42, -s * 0.55, -s * 0.02, -s * 0.65, -s * 0.18, -s * 0.95);
            ctx.moveTo(s * 0.22, -s * 0.35);
            ctx.bezierCurveTo(s * 0.42, -s * 0.55, s * 0.02, -s * 0.65, s * 0.18, -s * 0.95);
            ctx.stroke();
        },

        // Fork
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(0, s * 0.9);
            ctx.lineTo(0, -s * 0.2);
            ctx.moveTo(-s * 0.26, -s * 0.2);
            ctx.lineTo(-s * 0.26, -s * 0.82);
            ctx.moveTo(0, -s * 0.2);
            ctx.lineTo(0, -s * 0.86);
            ctx.moveTo(s * 0.26, -s * 0.2);
            ctx.lineTo(s * 0.26, -s * 0.82);
            ctx.stroke();
        },

        // Spoon
        function (ctx, s) {
            ctx.beginPath();
            ctx.ellipse(0, -s * 0.48, s * 0.26, s * 0.4, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.08);
            ctx.lineTo(0, s * 0.9);
            ctx.stroke();
        },

        // Plate
        function (ctx, s) {
            wobbleCircle(ctx, 0, 0, s * 0.8, 30);
            wobbleCircle(ctx, 0, 0, s * 0.48, 24);
        },

        // Cheese wedge with holes
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(-s * 0.75, s * 0.5);
            ctx.lineTo(s * 0.75, s * 0.5);
            ctx.lineTo(s * 0.45, -s * 0.55);
            ctx.closePath();
            ctx.stroke();
            [ [-s * 0.15, s * 0.1, s * 0.08], [s * 0.28, s * 0.28, s * 0.11], [s * 0.02, s * 0.34, s * 0.06] ]
                .forEach(function (h) {
                    ctx.beginPath();
                    ctx.arc(h[0], h[1], h[2], 0, Math.PI * 2);
                    ctx.stroke();
                });
        },

        // Wheat sprig
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(0, s * 0.9);
            ctx.lineTo(0, -s * 0.85);
            ctx.stroke();
            ctx.beginPath();
            for (let i = 0; i < 5; i++) {
                const y = -s * 0.72 + i * s * 0.3;
                ctx.moveTo(0, y);
                ctx.lineTo(-s * 0.3, y - s * 0.16);
                ctx.moveTo(0, y);
                ctx.lineTo(s * 0.3, y - s * 0.16);
            }
            ctx.stroke();
        },

        // Sparkle
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(0, -s * 0.55);
            ctx.lineTo(0, s * 0.55);
            ctx.moveTo(-s * 0.55, 0);
            ctx.lineTo(s * 0.55, 0);
            ctx.stroke();
        },

        // Little heart
        function (ctx, s) {
            ctx.beginPath();
            ctx.moveTo(0, s * 0.5);
            ctx.bezierCurveTo(-s * 0.9, -s * 0.1, -s * 0.35, -s * 0.85, 0, -s * 0.32);
            ctx.bezierCurveTo(s * 0.35, -s * 0.85, s * 0.9, -s * 0.1, 0, s * 0.5);
            ctx.stroke();
        },

        // Squiggle filler
        function (ctx, s) {
            ctx.beginPath();
            for (let x = -s; x <= s; x += 4) {
                const y = Math.sin(x * 0.14) * s * 0.22;
                if (x === -s) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
    ];

    /* ---------- Seamless doodle tile ---------- */

    function createDoodleTexture() {
        const size = 512;
        const grid = 4;
        const cell = size / grid;

        const c = document.createElement('canvas');
        c.width = c.height = size;
        const ctx = c.getContext('2d');

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.88)';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        for (let gy = 0; gy < grid; gy++) {
            for (let gx = 0; gx < grid; gx++) {
                if (Math.random() < 0.14) continue; // leave some breathing room

                const doodle = DOODLES[(Math.random() * DOODLES.length) | 0];

                ctx.save();
                ctx.translate(
                    gx * cell + cell / 2 + rand(-10, 10),
                    gy * cell + cell / 2 + rand(-10, 10)
                );
                ctx.rotate(rand(-0.5, 0.5));
                const scale = rand(0.72, 1.02) * (cell / 128);
                ctx.scale(scale, scale);
                doodle(ctx, 40);
                ctx.restore();
            }
        }

        return new THREE.CanvasTexture(c);
    }

    /* ---------- Waving cloth layers ---------- */

    const LAYERS = [
        {
            z: -34,
            tint: 0xe5c05b,      // champagne gold ink
            opacity: 0.19,
            repeat: [7, 4],
            drift: 0.006,
            waveAmp: 2.4,
            waveSpeed: 0.5,
            tilt: -0.05
        },
        {
            z: -74,
            tint: 0x5fae8a,      // moss green ink
            opacity: 0.12,
            repeat: [7, 4],
            drift: -0.0035,
            waveAmp: 4.0,
            waveSpeed: 0.3,
            tilt: 0.04
        }
    ];

    function buildLayer(config) {
        const distance = camera.position.z - config.z;
        const viewHeight = 2 * distance * Math.tan((camera.fov * Math.PI / 180) / 2);
        const width = viewHeight * 2.5;   // wide enough for ultra-wide screens
        const height = viewHeight * 1.4;

        const geometry = new THREE.PlaneGeometry(
            width,
            height,
            isMobile ? 36 : 64,
            isMobile ? 22 : 40
        );

        const texture = createDoodleTexture();
        texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
        texture.repeat.set(config.repeat[0], config.repeat[1]);
        texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());

        const material = new THREE.MeshBasicMaterial({
            map: texture,
            color: config.tint,
            transparent: true,
            opacity: config.opacity,
            depthWrite: false
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(0, -2, config.z);
        mesh.rotation.x = config.tilt;
        scene.add(mesh);

        return {
            mesh: mesh,
            texture: texture,
            config: config,
            basePositions: Float32Array.from(geometry.attributes.position.array),
            phase: rand(0, Math.PI * 2)
        };
    }

    function updateLayer(layer, seconds, dt) {
        const position = layer.mesh.geometry.attributes.position;
        const array = position.array;
        const base = layer.basePositions;
        const amp = layer.config.waveAmp;
        const t = seconds * layer.config.waveSpeed + layer.phase;

        for (let i = 0; i < position.count; i++) {
            const bx = base[i * 3];
            const by = base[i * 3 + 1];
            array[i * 3 + 2] =
                Math.sin(bx * 0.045 + t) * amp +
                Math.cos(by * 0.06 + t * 0.8) * amp * 0.6;
        }

        position.needsUpdate = true;

        // Endless pattern drift
        layer.texture.offset.x += layer.config.drift * dt;
        layer.texture.offset.y += layer.config.drift * dt * 0.35;
    }

    /* ---------- Lifecycle ---------- */

    function init() {
        try {
            scene = new THREE.Scene();
            scene.fog = new THREE.Fog(FOG_COLOR, 120, 260);

            camera = new THREE.PerspectiveCamera(
                55,
                canvas.clientWidth / canvas.clientHeight,
                0.1,
                1000
            );
            camera.position.z = 85;

            renderer = new THREE.WebGLRenderer({
                canvas: canvas,
                alpha: true,
                antialias: true,
                powerPreference: 'high-performance'
            });
            renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

            clock = new THREE.Clock();

            LAYERS.forEach(function (config) {
                layers.push(buildLayer(config));
            });

            // Event Listeners
            window.addEventListener('resize', onWindowResize, { passive: true });
            document.addEventListener('mousemove', onDocumentMouseMove, { passive: true });

            // Touch interaction for mobile
            canvas.addEventListener('touchmove', onTouchMove, { passive: true });

            // Battery-saving Intersection Observer
            if ('IntersectionObserver' in window) {
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach((entry) => {
                        isVisible = entry.isIntersecting;
                        if (isVisible && !animationFrameId) {
                            animate();
                        }
                    });
                }, { threshold: 0.05 });
                observer.observe(canvas);
            }

            animate();
        } catch (e) {
            console.warn('SharePlate doodle tapestry initialization skipped:', e);
            canvas.style.display = 'none';
        }
    }

    function onWindowResize() {
        if (!canvas) return;
        windowHalfX = window.innerWidth / 2;
        windowHalfY = window.innerHeight / 2;

        const width = canvas.parentElement.clientWidth;
        const height = canvas.parentElement.clientHeight;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
    }

    function onDocumentMouseMove(event) {
        mouseX = (event.clientX - windowHalfX) * 0.035;
        mouseY = (event.clientY - windowHalfY) * 0.035;
    }

    function onTouchMove(event) {
        if (event.touches.length > 0) {
            mouseX = (event.touches[0].clientX - windowHalfX) * 0.03;
            mouseY = (event.touches[0].clientY - windowHalfY) * 0.03;
        }
    }

    function animate() {
        if (!isVisible) {
            animationFrameId = null;
            return;
        }

        animationFrameId = requestAnimationFrame(animate);

        const dt = Math.min(clock.getDelta(), 0.05);
        const t = performance.now();
        const seconds = t * 0.001;

        // Smooth the mouse into a restrained parallax
        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        // Very slow autonomous camera drift so the tapestry breathes
        const driftX = Math.sin(t * 0.00012) * 4;
        const driftY = Math.cos(t * 0.00009) * 2.5;

        camera.position.x = driftX + targetX * 0.25;
        camera.position.y = driftY + targetY * 0.18;
        camera.lookAt(0, -2, 0);

        layers.forEach(function (layer) {
            updateLayer(layer, seconds, dt);
        });

        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
