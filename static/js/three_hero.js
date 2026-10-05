/**
 * FoodBridge 3D WebGL Interactive Hero Network
 * Built with Three.js (r128)
 * Inspired by modern tech interactive canvases (e.g. hackspire.tech)
 */

(function () {
    'use strict';

    const canvas = document.getElementById('hero3d-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    let scene, camera, renderer;
    let nodesMesh, linesMesh, particleMesh, centralNodes = [];
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let windowHalfX = window.innerWidth / 2;
    let windowHalfY = window.innerHeight / 2;
    let animationFrameId = null;
    let isVisible = true;

    // Node Count & Constellation Parameters
    const NODE_COUNT = window.innerWidth < 768 ? 32 : 65;
    const MAX_DISTANCE = 38;
    const nodePositions = [];
    const nodeVelocities = [];

    function init() {
        try {
            scene = new THREE.Scene();

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

            buildNetwork();
            buildParticles();
            buildCentralHubs();

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
            console.warn('FoodBridge 3D WebGL initialization skipped:', e);
            canvas.style.display = 'none';
        }
    }

    // Helper: circular glowing texture
    function createGlowTexture(colorHex) {
        const size = 64;
        const c = document.createElement('canvas');
        c.width = size;
        c.height = size;
        const ctx = c.getContext('2d');
        const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
        gradient.addColorStop(0, colorHex);
        gradient.addColorStop(0.35, colorHex);
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, size, size);
        return new THREE.CanvasTexture(c);
    }

    function buildCentralHubs() {
        const hubGroup = new THREE.Group();
        const hubData = [
            { color: 0x10b981, pos: [-24, 8, 5], label: 'Donors' },
            { color: 0xf59e0b, pos: [22, -6, 10], label: 'Volunteers' },
            { color: 0x34d399, pos: [0, 18, -8], label: 'NGOs' }
        ];

        hubData.forEach((hub) => {
            // Core sphere
            const geom = new THREE.SphereGeometry(1.6, 16, 16);
            const mat = new THREE.MeshBasicMaterial({
                color: hub.color,
                wireframe: true,
                transparent: true,
                opacity: 0.85
            });
            const mesh = new THREE.Mesh(geom, mat);
            mesh.position.set(...hub.pos);

            // Halo ring
            const ringGeom = new THREE.RingGeometry(2.2, 2.6, 24);
            const ringMat = new THREE.MeshBasicMaterial({
                color: hub.color,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.4
            });
            const ringMesh = new THREE.Mesh(ringGeom, ringMat);
            mesh.add(ringMesh);

            hubGroup.add(mesh);
            centralNodes.push({ mesh, ring: ringMesh, speed: Math.random() * 0.02 + 0.01 });
        });

        scene.add(hubGroup);
    }

    function buildNetwork() {
        const positions = new Float32Array(NODE_COUNT * 3);
        const spread = window.innerWidth < 768 ? 45 : 75;

        for (let i = 0; i < NODE_COUNT; i++) {
            const x = (Math.random() - 0.5) * spread;
            const y = (Math.random() - 0.5) * spread * 0.7;
            const z = (Math.random() - 0.5) * 45;

            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = z;

            nodePositions.push(new THREE.Vector3(x, y, z));
            nodeVelocities.push(
                new THREE.Vector3(
                    (Math.random() - 0.5) * 0.045,
                    (Math.random() - 0.5) * 0.045,
                    (Math.random() - 0.5) * 0.025
                )
            );
        }

        const pointGeometry = new THREE.BufferGeometry();
        pointGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const pointMaterial = new THREE.PointsMaterial({
            size: 3.2,
            map: createGlowTexture('#10b981'),
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        nodesMesh = new THREE.Points(pointGeometry, pointMaterial);
        scene.add(nodesMesh);

        // Dynamic Line Mesh
        const lineGeometry = new THREE.BufferGeometry();
        const maxLines = NODE_COUNT * 12;
        const linePositions = new Float32Array(maxLines * 6);
        const lineColors = new Float32Array(maxLines * 6);

        lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3).setUsage(THREE.DynamicDrawUsage));
        lineGeometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3).setUsage(THREE.DynamicDrawUsage));

        const lineMaterial = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            opacity: 0.65
        });

        linesMesh = new THREE.LineSegments(lineGeometry, lineMaterial);
        scene.add(linesMesh);
    }

    function buildParticles() {
        const particleCount = 80;
        const geom = new THREE.BufferGeometry();
        const pos = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount * 3; i += 3) {
            pos[i] = (Math.random() - 0.5) * 110;
            pos[i + 1] = (Math.random() - 0.5) * 90;
            pos[i + 2] = (Math.random() - 0.5) * 80;
        }

        geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({
            size: 2.2,
            map: createGlowTexture('#f59e0b'),
            transparent: true,
            opacity: 0.55,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        particleMesh = new THREE.Points(geom, mat);
        scene.add(particleMesh);
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

    function updateNodes() {
        const linePositions = linesMesh.geometry.attributes.position.array;
        const lineColors = linesMesh.geometry.attributes.color.array;
        let lineVertexIndex = 0;
        let lineCount = 0;

        const spread = window.innerWidth < 768 ? 45 : 75;
        const halfSpread = spread / 2;

        for (let i = 0; i < NODE_COUNT; i++) {
            const p = nodePositions[i];
            const v = nodeVelocities[i];

            p.add(v);

            if (p.x < -halfSpread || p.x > halfSpread) v.x = -v.x;
            if (p.y < -halfSpread * 0.6 || p.y > halfSpread * 0.6) v.y = -v.y;
            if (p.z < -25 || p.z > 25) v.z = -v.z;

            // Connect nearby nodes
            for (let j = i + 1; j < NODE_COUNT; j++) {
                const pj = nodePositions[j];
                const dx = p.x - pj.x;
                const dy = p.y - pj.y;
                const dz = p.z - pj.z;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                if (dist < MAX_DISTANCE && lineVertexIndex + 6 < linePositions.length) {
                    const alpha = 1.0 - (dist / MAX_DISTANCE);

                    linePositions[lineVertexIndex] = p.x;
                    linePositions[lineVertexIndex + 1] = p.y;
                    linePositions[lineVertexIndex + 2] = p.z;

                    linePositions[lineVertexIndex + 3] = pj.x;
                    linePositions[lineVertexIndex + 4] = pj.y;
                    linePositions[lineVertexIndex + 5] = pj.z;

                    // Emerald to gold gradient lines
                    lineColors[lineVertexIndex] = 0.06;
                    lineColors[lineVertexIndex + 1] = 0.72 * alpha;
                    lineColors[lineVertexIndex + 2] = 0.50 * alpha;

                    lineColors[lineVertexIndex + 3] = 0.96 * alpha;
                    lineColors[lineVertexIndex + 4] = 0.62 * alpha;
                    lineColors[lineVertexIndex + 5] = 0.04;

                    lineVertexIndex += 6;
                    lineCount++;
                }
            }
        }

        // Update positions buffer
        const pointPositions = nodesMesh.geometry.attributes.position.array;
        for (let i = 0; i < NODE_COUNT; i++) {
            pointPositions[i * 3] = nodePositions[i].x;
            pointPositions[i * 3 + 1] = nodePositions[i].y;
            pointPositions[i * 3 + 2] = nodePositions[i].z;
        }

        nodesMesh.geometry.attributes.position.needsUpdate = true;
        linesMesh.geometry.attributes.position.needsUpdate = true;
        linesMesh.geometry.attributes.color.needsUpdate = true;
        linesMesh.geometry.setDrawRange(0, lineCount * 2);
    }

    function animate() {
        if (!isVisible) {
            animationFrameId = null;
            return;
        }

        animationFrameId = requestAnimationFrame(animate);

        // Smooth camera lerp
        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        scene.rotation.y = targetX * 0.012;
        scene.rotation.x = targetY * 0.008;

        // Animate central hubs
        centralNodes.forEach((node, idx) => {
            node.mesh.rotation.y += node.speed;
            node.mesh.rotation.x += node.speed * 0.7;
            node.ring.rotation.z += (idx % 2 === 0 ? 0.015 : -0.015);
        });

        // Rotate ambient particles
        if (particleMesh) {
            particleMesh.rotation.y += 0.0008;
            particleMesh.rotation.x += 0.0004;
        }

        updateNodes();
        renderer.render(scene, camera);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
