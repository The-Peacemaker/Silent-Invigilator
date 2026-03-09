/* ═══════════════════════════════════════════════════════════
   THE SILENT INVIGILATOR — Homepage Controller
   Particle canvas, scroll animations, navbar effects
   ═══════════════════════════════════════════════════════════ */

/* ── PARTICLE CANVAS ────────────────────────────────────── */
(function initParticles() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let w, h, particles;
    const PARTICLE_COUNT = 60;
    const CONNECTION_DIST = 150;

    function resize() {
        w = canvas.width = canvas.parentElement.offsetWidth;
        h = canvas.height = canvas.parentElement.offsetHeight;
    }

    function createParticles() {
        particles = [];
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push({
                x: Math.random() * w,
                y: Math.random() * h,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                r: Math.random() * 2 + 1,
                opacity: Math.random() * 0.5 + 0.1,
            });
        }
    }

    function draw() {
        ctx.clearRect(0, 0, w, h);

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < CONNECTION_DIST) {
                    const alpha = (1 - dist / CONNECTION_DIST) * 0.15;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }

        // Draw particles
        particles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 212, 255, ${p.opacity})`;
            ctx.fill();

            // Move
            p.x += p.vx;
            p.y += p.vy;

            // Wrap edges
            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;
        });

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', () => { resize(); });
    resize();
    createParticles();
    draw();
})();

/* ── NAVBAR SCROLL EFFECT ───────────────────────────────── */
(function initNavbar() {
    const navbar = document.getElementById('main-navbar');
    if (!navbar) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
})();

/* ── SCROLL-REVEAL ANIMATIONS ───────────────────────────── */
(function initScrollReveal() {
    const elements = document.querySelectorAll('.animate-fade-up');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    elements.forEach(el => observer.observe(el));
})();

/* ── SMOOTH SCROLL for anchor links ─────────────────────── */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});
