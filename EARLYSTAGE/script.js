/* =========================================================
   LionexAI - Early Stage Landing
   Modular vanilla JS: nav, scroll reveal, particle canvas, form
   ========================================================= */
(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* ---------------------------------------------------------
     1. Sticky nav state + active link highlighting
     --------------------------------------------------------- */
  function initNav() {
    const nav = document.getElementById("nav");
    const toggle = document.getElementById("navToggle");
    const menu = document.getElementById("navMenu");
    const links = Array.from(document.querySelectorAll(".nav__link"));

    // Shadow / background when scrolled
    const onScroll = () => {
      nav.classList.toggle("is-scrolled", window.scrollY > 10);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    // Mobile hamburger toggle
    toggle.addEventListener("click", () => {
      const open = menu.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });

    // Close mobile menu after clicking a link
    links.forEach((link) => {
      link.addEventListener("click", () => {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });

    // Active link via section visibility
    const sections = links
      .map((l) => document.querySelector(l.getAttribute("href")))
      .filter(Boolean);

    if ("IntersectionObserver" in window && sections.length) {
      const spy = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const id = entry.target.id;
              links.forEach((l) =>
                l.classList.toggle(
                  "is-active",
                  l.getAttribute("href") === "#" + id
                )
              );
            }
          });
        },
        { rootMargin: "-45% 0px -50% 0px" }
      );
      sections.forEach((s) => spy.observe(s));
    }
  }

  /* ---------------------------------------------------------
     2. Scroll reveal animations
     --------------------------------------------------------- */
  function initReveal() {
    const items = document.querySelectorAll(".reveal");
    if (!items.length) return;

    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      items.forEach((el) => el.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry, i) => {
          if (entry.isIntersecting) {
            // Subtle stagger within a viewport batch
            setTimeout(() => entry.target.classList.add("is-visible"), i * 70);
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
    );
    items.forEach((el) => observer.observe(el));
  }

  /* ---------------------------------------------------------
     3. Hero particle network (lightweight, perf-capped)
     --------------------------------------------------------- */
  function initParticles() {
    const canvas = document.getElementById("heroCanvas");
    if (!canvas || prefersReducedMotion) return;

    const ctx = canvas.getContext("2d");
    let width, height, dpr, particles, rafId;
    let running = false;

    const COLORS = ["#d4af52", "#1fb6a6", "#4fd6c6"];

    function size() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function build() {
      // Scale particle count to viewport, capped for performance
      const count = Math.min(70, Math.floor((width * height) / 16000));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.8 + 0.8,
        c: COLORS[(Math.random() * COLORS.length) | 0],
      }));
    }

    function draw() {
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Connecting lines
        for (let j = i + 1; j < particles.length; j++) {
          const q = particles[j];
          const dx = p.x - q.x;
          const dy = p.y - q.y;
          const dist = dx * dx + dy * dy;
          if (dist < 14000) {
            ctx.globalAlpha = (1 - dist / 14000) * 0.28;
            ctx.strokeStyle = "#1fb6a6";
            ctx.lineWidth = 0.6;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.stroke();
          }
        }
      }

      // Dots on top
      for (const p of particles) {
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = p.c;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      rafId = requestAnimationFrame(draw);
    }

    function start() {
      if (running) return;
      running = true;
      draw();
    }
    function stop() {
      running = false;
      cancelAnimationFrame(rafId);
    }

    function reset() {
      size();
      build();
    }

    reset();
    start();

    // Resize handling (debounced)
    let t;
    window.addEventListener("resize", () => {
      clearTimeout(t);
      t = setTimeout(reset, 200);
    });

    // Pause animation when hero is off-screen
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => (e.isIntersecting ? start() : stop()));
        },
        { threshold: 0 }
      );
      io.observe(canvas);
    }

    // Pause when tab hidden
    document.addEventListener("visibilitychange", () => {
      document.hidden ? stop() : start();
    });
  }

  /* ---------------------------------------------------------
     4. Contact form - client-side validation only
     --------------------------------------------------------- */
  function initForm() {
    const form = document.getElementById("signupForm");
    if (!form) return;

    const success = document.getElementById("formSuccess");
    const fields = {
      name: form.querySelector("#name"),
      email: form.querySelector("#email"),
    };
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function setError(input, message) {
      const slot = form.querySelector(
        `[data-error-for="${input.id}"]`
      );
      input.classList.toggle("is-invalid", Boolean(message));
      input.setAttribute("aria-invalid", message ? "true" : "false");
      if (slot) slot.textContent = message || "";
      return !message;
    }

    function validate() {
      let ok = true;
      ok = setError(
        fields.name,
        fields.name.value.trim() ? "" : "Please enter your name."
      ) && ok;
      const email = fields.email.value.trim();
      ok = setError(
        fields.email,
        !email
          ? "Please enter your email."
          : emailRe.test(email)
          ? ""
          : "Please enter a valid email address."
      ) && ok;
      return ok;
    }

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!validate()) return;
      // No backend: show inline confirmation and reset.
      success.hidden = false;
      form.reset();
      setError(fields.name, "");
      setError(fields.email, "");
    });

    // Clear an error as the user corrects it
    Object.values(fields).forEach((input) => {
      input.addEventListener("input", () => {
        if (input.classList.contains("is-invalid")) setError(input, "");
        success.hidden = true;
      });
    });
  }

  /* ---------------------------------------------------------
     Init on DOM ready
     --------------------------------------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    initNav();
    initReveal();
    initParticles();
    initForm();
  });
})();
