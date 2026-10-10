/* =========================================================================
   VAEL — Landing page
   JS vanilla. IntersectionObserver + CSS nativo, sin librerías.
   Todo lo animado aquí es transform/opacity (y el stroke del anillo).
   ========================================================================= */
(function () {
  'use strict';

  /* ===================== CONFIGURACIÓN ===================== */
  // URL del panel de administración. Vacío = botón deshabilitado.
  // Cuando se compre el dominio, poner aquí: 'https://app.vael.ai/login'
  const ADMIN_LOGIN_URL = '';
  /* ========================================================= */

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

  /* --------------------------------------------------------------------- */
  /* 1. NAV: fondo con blur al scrollear + menú móvil                      */
  /* --------------------------------------------------------------------- */
  var nav = $('#nav');
  var navToggle = $('#nav-toggle');
  var navLinks = $('#nav-links');

  (function initNav() {
    if (!nav) return;

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        nav.classList.toggle('is-scrolled', window.scrollY > 8);
        ticking = false;
      });
    }
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });

    if (!navToggle || !navLinks) return;

    function setOpen(open) {
      nav.classList.toggle('is-open', open);
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      $('.sr-only', navToggle).textContent = open ? 'Cerrar menú' : 'Abrir menú';
    }

    navToggle.addEventListener('click', function () {
      setOpen(!nav.classList.contains('is-open'));
    });

    navLinks.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        setOpen(false);
        navToggle.focus();
      }
    });

    document.addEventListener('click', function (e) {
      if (!nav.contains(e.target) && nav.classList.contains('is-open')) setOpen(false);
    });
  })();

  /* --------------------------------------------------------------------- */
  /* 1.b Botón de acceso al panel: se activa solo si hay dominio           */
  /* --------------------------------------------------------------------- */
  (function initAdminLogin() {
    var link = $('#admin-login');
    if (!link) return;

    var url = String(ADMIN_LOGIN_URL || '').trim();

    if (url) {
      link.setAttribute('href', url);
      link.removeAttribute('aria-disabled');
      link.removeAttribute('title');
      link.classList.remove('is-disabled');
      return;
    }

    // Sin dominio todavía: visible pero inerte. Al no tener href no es
    // enfocable ni navegable, así que no hay enlace roto que publicar.
    link.removeAttribute('href');
    link.setAttribute('role', 'link');
    link.setAttribute('aria-disabled', 'true');
    link.setAttribute('title', 'Disponible próximamente');
    link.classList.add('is-disabled');

    link.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
    });
  })();

  /* --------------------------------------------------------------------- */
  /* 2. Contador numérico reutilizable                                     */
  /* --------------------------------------------------------------------- */
  function countTo(el, target, duration) {
    if (!el) return;
    if (reduceMotion) { el.textContent = String(target); return; }

    var start = null;
    var total = duration || 1200;

    function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

    function frame(now) {
      if (start === null) start = now;
      var p = Math.min((now - start) / total, 1);
      el.textContent = String(Math.round(easeOut(p) * target));
      if (p < 1) window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }

  /* --------------------------------------------------------------------- */
  /* 3. HERO: puntaje 0 → 87 y anillo que se llena                         */
  /* --------------------------------------------------------------------- */
  (function initHeroScore() {
    var ring = $('#ring-fill');
    var scoreEl = $('#hero-score');
    var mock = $('#mock');
    var SCORE = 87;

    if (ring) {
      var r = ring.r.baseVal.value;
      var circumference = 2 * Math.PI * r;
      ring.style.strokeDasharray = circumference + ' ' + circumference;
      ring.style.strokeDashoffset = String(circumference);

      window.requestAnimationFrame(function () {
        // Fuerza el cálculo del valor inicial para que la transición sí ocurra
        void ring.getBoundingClientRect();
        ring.style.strokeDashoffset = String(circumference * (1 - SCORE / 100));
      });
    }

    if (mock) {
      // Dispara el llenado de las barras del mockup
      window.setTimeout(function () { mock.classList.add('is-filled'); }, reduceMotion ? 0 : 420);
    }

    window.setTimeout(function () { countTo(scoreEl, SCORE, 1100); }, reduceMotion ? 0 : 340);
  })();

  /* --------------------------------------------------------------------- */
  /* 4. Video del producto: sólo se muestra si carga de verdad             */
  /* --------------------------------------------------------------------- */
  (function initVideo() {
    var video = $('#demo-video');
    var screen = $('#screen');
    if (!video || !screen) return;

    function show() { screen.classList.add('has-video'); }
    function hide() { screen.classList.remove('has-video'); }

    video.addEventListener('loadeddata', show);
    video.addEventListener('error', hide);
    if (video.readyState >= 2) show();

    // Si no hay archivo todavía, el mockup HTML queda como visual del hero.
  })();

  /* --------------------------------------------------------------------- */
  /* 5. Reveals al scroll (una sola vez)                                   */
  /* --------------------------------------------------------------------- */
  (function initReveals() {
    var items = $$('.reveal');
    if (!items.length) return;

    if (reduceMotion || !('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -100px 0px', threshold: 0.01 });

    items.forEach(function (el) { io.observe(el); });
  })();

  /* --------------------------------------------------------------------- */
  /* 6. CÓMO FUNCIONA: panel sticky sincronizado con los pasos             */
  /* --------------------------------------------------------------------- */
  (function initHowItWorks() {
    var steps = $$('#hiw-steps .step');
    var panels = $$('#hiw-stage .stage__panel');
    if (!steps.length || !panels.length) return;

    function activate(index) {
      panels.forEach(function (p, i) { p.classList.toggle('is-active', i === index); });
      steps.forEach(function (s, i) { s.classList.toggle('is-current', i === index); });
    }

    activate(0);

    if (!('IntersectionObserver' in window)) {
      steps.forEach(function (s) { s.classList.add('is-current'); });
      panels.forEach(function (p) { p.classList.add('is-active'); });
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      // El paso más centrado en el viewport manda
      var best = null;
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        if (!best || entry.intersectionRatio > best.intersectionRatio) best = entry;
      });
      if (!best) return;
      activate(steps.indexOf(best.target));
    }, { rootMargin: '-40% 0px -40% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] });

    steps.forEach(function (s) { io.observe(s); });
  })();

  /* --------------------------------------------------------------------- */
  /* 7. SCORE: medidores + números que cuentan al entrar en viewport       */
  /* --------------------------------------------------------------------- */
  (function initFormula() {
    var formula = $('#formula');
    if (!formula) return;

    function run() {
      formula.classList.add('is-filled');
      countTo($('#score-total'), 87, 1200);
      $$('[data-count]', formula).forEach(function (el, i) {
        var target = parseInt(el.getAttribute('data-count'), 10) || 0;
        window.setTimeout(function () { countTo(el, target, 900); }, reduceMotion ? 0 : i * 110);
      });
    }

    if (!('IntersectionObserver' in window)) { run(); return; }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        run();
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -80px 0px', threshold: 0.2 });

    io.observe(formula);
  })();

  /* --------------------------------------------------------------------- */
  /* 8. Glow que sigue al cursor, sólo dentro de la tarjeta del hero       */
  /* --------------------------------------------------------------------- */
  (function initHeroGlow() {
    var card = $('#hero-card');
    var glow = $('#hero-glow');
    if (!card || !glow || reduceMotion) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    var pending = false;
    var x = 0, y = 0;

    function paint() {
      glow.style.transform = 'translate3d(' + x + 'px,' + y + 'px,0)';
      pending = false;
    }

    card.addEventListener('pointermove', function (e) {
      var rect = card.getBoundingClientRect();
      x = e.clientX - rect.left;
      y = e.clientY - rect.top;
      if (!pending) { pending = true; window.requestAnimationFrame(paint); }
    });

    card.addEventListener('pointerenter', function () { card.classList.add('is-glowing'); });
    card.addEventListener('pointerleave', function () { card.classList.remove('is-glowing'); });
  })();

  /* --------------------------------------------------------------------- */
  /* 9. Mini-visual de la tarjeta grande: la fila destacada rota           */
  /* --------------------------------------------------------------------- */
  (function initFeatureViz() {
    var viz = $('#f-viz');
    if (!viz || reduceMotion) return;

    var rows = $$('.f-viz__rows li', viz);
    if (rows.length < 2) return;

    var i = 0;
    var timer = null;

    function tick() {
      i = (i + 1) % rows.length;
      rows.forEach(function (row, n) { row.classList.toggle('is-on', n === i); });
    }

    function start() { if (!timer) timer = window.setInterval(tick, 2200); }
    function stop() { if (timer) { window.clearInterval(timer); timer = null; } }

    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) { entry.isIntersecting ? start() : stop(); });
      }, { threshold: 0.3 });
      io.observe(viz);
    } else {
      start();
    }

    document.addEventListener('visibilitychange', function () {
      document.hidden ? stop() : start();
    });
  })();

  /* --------------------------------------------------------------------- */
  /* 10. Formulario de demo                                                */
  /* --------------------------------------------------------------------- */
  (function initForm() {
    var form = $('#demo-form');
    var input = $('#email');
    var msg = $('#form-msg');
    if (!form || !input || !msg) return;

    var EMAIL = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var value = input.value.trim();

      if (!EMAIL.test(value)) {
        input.setAttribute('aria-invalid', 'true');
        msg.classList.add('is-error');
        msg.textContent = 'Escribe un correo válido para poder responderte.';
        input.focus();
        return;
      }

      input.removeAttribute('aria-invalid');
      msg.classList.remove('is-error');
      msg.textContent = 'Listo. Te escribimos a ' + value + ' para coordinar la demo.';
      form.reset();

      // TODO: conectar con el endpoint real del formulario (ver action del <form>).
    });

    input.addEventListener('input', function () {
      if (input.getAttribute('aria-invalid') === 'true') {
        input.removeAttribute('aria-invalid');
        msg.textContent = '';
        msg.classList.remove('is-error');
      }
    });
  })();

  /* --------------------------------------------------------------------- */
  /* 11. Año del footer                                                    */
  /* --------------------------------------------------------------------- */
  (function initYear() {
    var el = $('#year');
    if (el) el.textContent = String(new Date().getFullYear());
  })();
})();
