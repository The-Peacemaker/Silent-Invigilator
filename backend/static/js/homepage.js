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

/* ── 3D VIDEO SCROLL ANIMATION (GSAP) ───────────────────── */
(function initVideoScroll() {
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;
    gsap.registerPlugin(ScrollTrigger);

    const video = document.getElementById("hero-video");
    const container = document.getElementById("ai-vision-scroll");
    
    if (!video || !container) return;

    let initAttempted = false;

    function initTrigger() {
        if (initAttempted) return;
        if (!video.duration || !isFinite(video.duration)) {
             setTimeout(initTrigger, 100);
             return;
        }
        initAttempted = true;
        
        // Pause video to manually scrub
        video.pause();
        
        // 1. Create the ScrollTrigger to pin the container
        let tl = gsap.timeline({
            scrollTrigger: {
                trigger: container,
                start: "top top",
                end: "+=500%", // Longer scroll distance for slower scrub
                pin: true, // Keep the section pinned while scrubbing
                scrub: 1, // Smooth scrubbing
                onUpdate: (self) => {
                    // This directly updates the video time based on scroll progress
                    if (video.duration && isFinite(video.duration)) {
                        // Cap at exactly 90% of the video to never hit the frozen end frame
                        video.currentTime = self.progress * (video.duration * 0.90); 
                    }
                }
            }
        });

        // 2. Animate the text overlays in sequence based on scroll %
        // Text 1: Fades in early, fades out
        tl.to("#msg-1", { opacity: 1, y: "-50%", duration: 1 })
          .to("#msg-1", { opacity: 0, y: "-70%", duration: 1 }, "+=0.5")
          
        // Text 2: Fades in next
          .to("#msg-2", { opacity: 1, y: "-50%", duration: 1 })
          .to("#msg-2", { opacity: 0, y: "-70%", duration: 1 }, "+=0.5")
          
        // Text 3: The powerful final statement
          .to("#msg-3", { opacity: 1, y: "-50%", duration: 1.5 })
          .to("#msg-3", { opacity: 0, scale: 1.2, duration: 1 }, "+=0.5");
    }

    if (video.readyState >= 1) {
        initTrigger();
    }
    video.addEventListener('loadedmetadata', initTrigger);
    
    // Fallback play if initialization totally fails
    setTimeout(() => {
        if (!initAttempted) video.play().catch(e => console.log(e));
    }, 2000);
})();
