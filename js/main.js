// SUM'IT — main.js

// Navigation active selon la page courante
document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.nav-link');
  const current = window.location.pathname.split('/').pop();
  links.forEach(link => {
    const href = (link.getAttribute('href') || '').split('/').pop();
    if (href === current) {
      links.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    }
  });
});

// Nav : passe en fond plein au scroll (la couleur vit dans le CSS, pas ici)
(function navScroll() {
  const update = () => {
    const nav = document.querySelector('.nav');
    if (nav) nav.classList.toggle('is-scrolled', window.scrollY > 40);
  };
  window.addEventListener('scroll', update, { passive: true });
  document.addEventListener('DOMContentLoaded', update);
})();

/* ══════════════════════════════════════════════════════════════
   Messages dans la page (remplacent les fenêtres alert du navigateur)
   sumitMessage(texte, { type: 'erreur' | 'info' | 'succes', pres: élément ou sélecteur,
                         duree: ms (0 = jusqu'à fermeture), action: { label, onClick } })
   ══════════════════════════════════════════════════════════════ */
(function messages() {
  let zone = null;
  const reduit = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function zoneToasts() {
    if (zone && document.body.contains(zone)) return zone;
    zone = document.createElement('div');
    zone.className = 'sumit-toasts';
    document.body.appendChild(zone);
    return zone;
  }

  function retirer(el) {
    if (!el || !el.isConnected) return;
    if (reduit()) { el.remove(); return; }
    el.classList.add('is-sortie');
    setTimeout(() => el.remove(), 180);
  }

  window.sumitMessage = function (texte, opts) {
    opts = opts || {};
    const alias = { error: 'erreur', success: 'succes', warning: 'info' };
    const type = alias[opts.type] || opts.type || 'info';
    const el = document.createElement('div');
    el.className = 'sumit-msg is-' + type;
    el.setAttribute('role', type === 'erreur' ? 'alert' : 'status');

    const p = document.createElement('p');
    p.textContent = texte;
    el.appendChild(p);

    if (opts.action && opts.action.label) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'sumit-msg-action';
      b.textContent = opts.action.label;
      b.addEventListener('click', () => { retirer(el); if (typeof opts.action.onClick === 'function') opts.action.onClick(); });
      el.appendChild(b);
    }
    const x = document.createElement('button');
    x.type = 'button';
    x.className = 'sumit-msg-fermer';
    x.setAttribute('aria-label', 'Fermer le message');
    x.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    x.addEventListener('click', () => retirer(el));
    el.appendChild(x);

    let cible = opts.pres;
    if (typeof cible === 'string') cible = document.querySelector(cible);
    if (cible) {
      // Un seul message à la fois sous un même élément
      const suivant = cible.nextElementSibling;
      if (suivant && suivant.classList.contains('sumit-msg')) suivant.remove();
      el.classList.add('is-inline');
      cible.insertAdjacentElement('afterend', el);
      if (opts.defiler !== false && el.scrollIntoView) {
        el.scrollIntoView({ block: 'nearest', behavior: reduit() ? 'auto' : 'smooth' });
      }
    } else {
      const z = zoneToasts();
      while (z.children.length >= 3) z.firstElementChild.remove();
      z.appendChild(el);
    }

    const duree = opts.duree != null ? opts.duree : (type === 'erreur' ? 9000 : 6000);
    if (duree > 0) {
      let t = setTimeout(() => retirer(el), duree);
      // On laisse le temps de lire : la minuterie s'arrête au survol ou au focus
      el.addEventListener('mouseenter', () => clearTimeout(t));
      el.addEventListener('focusin', () => clearTimeout(t));
      el.addEventListener('mouseleave', () => { clearTimeout(t); t = setTimeout(() => retirer(el), 3000); });
    }
    return el;
  };
})();

/* ══════════════════════════════════════════════════════════════
   Bibliothèques chargées à l'usage (carte, PDF, e-mail)
   ══════════════════════════════════════════════════════════════ */
(function chargements() {
  const promesses = {};
  window.chargerScript = function (src) {
    if (!promesses[src]) {
      promesses[src] = new Promise((ok, ko) => {
        const s = document.createElement('script');
        s.src = src;
        s.async = true;
        s.onload = () => ok();
        s.onerror = () => { delete promesses[src]; ko(new Error('Le module n\'a pas pu être chargé. Vérifie ta connexion.')); };
        document.head.appendChild(s);
      });
    }
    return promesses[src];
  };
  window.chargerStyle = function (href) {
    if (!promesses[href]) {
      promesses[href] = new Promise(ok => {
        const l = document.createElement('link');
        l.rel = 'stylesheet';
        l.href = href;
        l.onload = () => ok();
        l.onerror = () => ok();   // la carte reste utilisable sans sa feuille de style
        document.head.appendChild(l);
      });
    }
    return promesses[href];
  };
  window.chargerLeaflet = function () {
    if (window.L) return Promise.resolve(window.L);
    return Promise.all([
      chargerStyle('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'),
      chargerScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'),
    ]).then(() => window.L);
  };
  window.chargerOutilsPDF = function () {
    return Promise.all([
      chargerScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'),
      chargerScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'),
    ]);
  };
  window.chargerEmailJS = function () {
    return chargerScript('https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js').then(() => {
      if (!window.emailjs) throw new Error('Service d\'envoi indisponible');
      if (!window.__sumitEmailInit) { window.emailjs.init('rc324sv1XWdtOjTM6'); window.__sumitEmailInit = true; }
      return window.emailjs;
    });
  };
})();

/* ══════════════════════════════════════════════════════════════
   Mesure d'audience : anonyme, sans cookie, exemptée de consentement (CNIL).
   Rien n'identifie le visiteur : un numéro de visite tiré au hasard, effacé à la
   fermeture de l'onglet. Désactivable sur la page Confidentialité.
   ══════════════════════════════════════════════════════════════ */
(function mesureAudience() {
  function api() {
    if (typeof API_URL !== 'undefined') return API_URL;
    return (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
      ? 'http://localhost:8000' : 'https://sumit-web-s4lf.onrender.com';
  }
  function desactivee() {
    if (window.SUMIT_PAS_DE_MESURE) return true;
    try { if (localStorage.getItem('sumit_mesure_off') === '1') return true; } catch (e) {}
    if (navigator.globalPrivacyControl === true) return true;
    if (navigator.webdriver && !window.SUMIT_MESURE_TEST) return true;
    return false;
  }
  function visite() {
    try {
      let v = sessionStorage.getItem('sumit_visite');
      if (!v) { v = Math.random().toString(36).slice(2, 12); sessionStorage.setItem('sumit_visite', v); }
      return v;
    } catch (e) { return null; }
  }
  function appareil() {
    const w = Math.min(window.innerWidth || 0, (window.screen && screen.width) || 9999);
    return w < 600 ? 'telephone' : w < 1024 ? 'tablette' : 'ordinateur';
  }
  function connecte() { try { return !!localStorage.getItem('sumit_jwt'); } catch (e) { return false; } }
  function envoyer(charge) {
    if (desactivee()) return;
    const corps = JSON.stringify(charge);
    const url = api() + '/api/mesure';
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(url, new Blob([corps], { type: 'text/plain' }))) return;
    } catch (e) {}
    try { fetch(url, { method: 'POST', body: corps, keepalive: true, mode: 'no-cors', headers: { 'Content-Type': 'text/plain' } }); } catch (e) {}
  }
  window.sumitMesure = function (nom, detail) {
    envoyer({ t: 'evenement', n: nom, v: visite(), a: appareil(), c: connecte(), d: detail || undefined });
  };
  window.sumitMesureActive = function () { return !desactivee(); };
  function pageVue() {
    const p = new URLSearchParams(location.search);
    let source = p.get('utm_source') || null;
    if (!source && document.referrer) {
      try {
        const h = new URL(document.referrer).hostname.replace(/^www\./, '');
        if (h && h !== location.hostname) source = h;
      } catch (e) {}
    }
    envoyer({
      t: 'page', n: location.pathname.toLowerCase(), v: visite(),
      s: source, k: p.get('utm_campaign') || null, a: appareil(), c: connecte(),
    });
  }
  if (document.readyState === 'complete') pageVue();
  else window.addEventListener('load', pageVue, { once: true });
})();
