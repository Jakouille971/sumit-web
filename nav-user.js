// ══════════════════════════════════════════════════════════════
//  SUM'IT — nav-user.js v3
//  Garantit l'uniformité de la barre du haut sur tous les écrans :
//   - Liens : Accueil, Mon profil, Simulateur, Bilan, Mon compte, À venir
//   - Bouton « Se connecter » OU avatar utilisateur
//   - Menu plein écran sur téléphone
//  Les styles vivent dans css/style.css.
// ══════════════════════════════════════════════════════════════

(async function initNavUniforme() {
  const nav = document.querySelector('.nav');
  if (!nav) return;

  // Chaque étape est isolée : si l'une échoue (API endormie, script manquant…),
  // les autres s'exécutent quand même.
  const etape = (nom, fn) => { try { return fn(); } catch (e) { console.warn(`[nav] ${nom} :`, e); } };
  etape('moment', () => poserMomentDePage());
  etape('liens',  () => uniformiserLiens(nav));
  etape('burger', () => creerBurgerMenu(nav));
  try { await uniformiserUserSlot(nav); } catch (e) { console.warn('[nav] compte :', e); }
  etape('burger-position', () => {
    // Le burger doit rester juste avant le bloc utilisateur créé entre-temps
    const burger = nav.querySelector('.nav-burger');
    const user = nav.querySelector('#nav-user-container');
    if (burger && user && burger.nextElementSibling !== user) nav.insertBefore(burger, user);
  });
})();

// Conservé pour compatibilité : les styles sont désormais dans style.css
function injecterStylesNav() {}

// ── Identifiant de l'écran courant (utilisé par le CSS) ────────
function poserMomentDePage() {
  if (document.body.dataset.page) return;
  const p = window.location.pathname;
  const id = ['profil','simulateur','bilan','compte','avenir'].find(n => p.endsWith(n + '.html')) || 'home';
  document.body.dataset.page = id;
}

// ── Menu plein écran (téléphone) ───────────────────────────────
function creerBurgerMenu(nav) {
  if (nav.querySelector('.nav-burger')) return;

  const links = nav.querySelector('.nav-links');
  const burger = document.createElement('button');
  burger.type = 'button';
  burger.className = 'nav-burger';
  burger.setAttribute('aria-label', 'Ouvrir le menu');
  burger.setAttribute('aria-expanded', 'false');
  if (links) {
    if (!links.id) links.id = 'nav-links-menu';
    burger.setAttribute('aria-controls', links.id);
  }
  burger.innerHTML = '<span></span><span></span><span></span>';
  nav.classList.add('has-burger');

  const fermer = () => {
    burger.classList.remove('open');
    burger.setAttribute('aria-expanded', 'false');
    burger.setAttribute('aria-label', 'Ouvrir le menu');
    const l = nav.querySelector('.nav-links');
    if (l) l.classList.remove('mobile-open');
  };

  burger.addEventListener('click', () => {
    const l = nav.querySelector('.nav-links');
    const ouvert = burger.classList.toggle('open');
    burger.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    burger.setAttribute('aria-label', ouvert ? 'Fermer le menu' : 'Ouvrir le menu');
    if (l) l.classList.toggle('mobile-open', ouvert);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && burger.classList.contains('open')) { fermer(); burger.focus(); }
  });

  // Fermer le menu quand on clique sur un lien
  if (links) {
    links.addEventListener('click', (e) => {
      if (e.target.closest('.nav-link')) fermer();
    });
  }

  const userContainer = nav.querySelector('#nav-user-container');
  if (userContainer) nav.insertBefore(burger, userContainer);
  else nav.appendChild(burger);
}

// ── 1. Uniformiser les liens de navigation ─────────────────────
function uniformiserLiens(nav) {
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  const prefix = inPages ? '' : 'pages/';

  const LIENS_ATTENDUS = [
    { label: 'Accueil',    href: inPages ? '../' : '/',         id: 'home' },
    { label: 'Mon profil', href: `${prefix}profil.html`,        id: 'profil' },
    { label: 'Simulateur', href: `${prefix}simulateur.html`,    id: 'simulateur' },
    { label: 'Bilan',      href: `${prefix}bilan.html`,         id: 'bilan' },
    { label: 'Mon compte', href: `${prefix}compte.html`,        id: 'compte' },
    { label: 'À venir',    href: `${prefix}avenir.html`,        id: 'avenir' },
  ];

  const currentId =
    path.endsWith('profil.html')     ? 'profil' :
    path.endsWith('simulateur.html') ? 'simulateur' :
    path.endsWith('bilan.html')      ? 'bilan' :
    path.endsWith('avenir.html')     ? 'avenir' :
    path.endsWith('compte.html')     ? 'compte' :
    'home';

  let navLinks = nav.querySelector('.nav-links');
  if (!navLinks) {
    navLinks = document.createElement('div');
    navLinks.className = 'nav-links';
    nav.appendChild(navLinks);
  }

  navLinks.innerHTML = LIENS_ATTENDUS.map(lien => {
    const actif = lien.id === currentId;
    return `<a href="${lien.href}" class="nav-link${actif ? ' active' : ''}"${actif ? ' aria-current="page"' : ''}>${lien.label}</a>`;
  }).join('');
}

// ── 2. Bloc utilisateur (connexion OU avatar) + tutoriel ───────
async function uniformiserUserSlot(nav) {
  let container = document.getElementById('nav-user-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'nav-user-container';
    const oldCta = nav.querySelector('.nav-cta');
    if (oldCta) oldCta.remove();
    nav.appendChild(container);
  }

  // Affichage immédiat à partir de l'état local (token + cache) :
  // on ne bloque jamais sur fetchMe(), qui peut prendre 30 s si le serveur dort.
  const tutoBtnHTML = construireBtnTutoriel();
  const tokenPresent = (typeof isLoggedIn === 'function') && isLoggedIn();
  const cachedUser = (typeof getCachedUser === 'function') ? getCachedUser() : null;

  if (tokenPresent && cachedUser) {
    renderLoggedIn(container, cachedUser, tutoBtnHTML);
  } else if (tokenPresent) {
    renderLoggedIn(container, { prenom: 'Coureur', email: '' }, tutoBtnHTML);
  } else {
    renderLoggedOut(container, tutoBtnHTML);
  }

  // Enrichissement en arrière-plan
  if (tokenPresent && typeof fetchMe === 'function') {
    fetchMe().then(user => {
      renderLoggedIn(container, user, tutoBtnHTML);
    }).catch(e => {
      // Token invalide (401) → mode déconnecté ; simple coupure réseau → on garde l'affichage
      if (e && e.message && e.message.includes('expirée')) {
        if (typeof clearToken === 'function') clearToken();
        renderLoggedOut(container, tutoBtnHTML);
      }
    });
  }
}

function construireBtnTutoriel() {
  return `
    <button type="button" class="nav-tuto-btn" onclick="if(typeof demarrerOnboarding==='function'){demarrerOnboarding()}else{alert('Le tutoriel se charge, réessaie dans un instant.');}" title="Voir le tutoriel">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6"/>
        <path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        <circle cx="12" cy="16.9" r="0.95" fill="currentColor"/>
      </svg>
      <span>Tutoriel</span>
    </button>
  `;
}

function renderLoggedOut(container, tutoBtnHTML = '') {
  // Construit l'URL même si loginGoogle() n'est pas disponible
  const API_BASE = (typeof API_URL !== 'undefined') ? API_URL :
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8000'
      : 'https://sumit-web-s4lf.onrender.com');

  container.innerHTML = `
    ${tutoBtnHTML}
    <a href="${API_BASE}/api/auth/google/login" class="nav-login-btn">
      <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
        <path fill="currentColor" d="M21.35 11.1h-9.17v2.73h6.51c-.33 3.81-3.5 5.44-6.5 5.44C8.36 19.27 5 16.25 5 12c0-4.1 3.2-7.27 7.2-7.27 3.09 0 4.9 1.97 4.9 1.97L19 4.72S16.56 2 12.1 2C6.42 2 2.03 6.8 2.03 12c0 5.05 4.13 10 10.22 10 5.35 0 9.25-3.67 9.25-9.09 0-1.15-.15-1.81-.15-1.81z"/>
      </svg>
      Se connecter
    </a>
  `;
}

function echapperNav(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderLoggedIn(container, user, tutoBtnHTML = '') {
  const prenom = user.prenom || user.name?.split(' ')[0] || 'Coureur';
  const initiale = prenom[0]?.toUpperCase() || 'C';
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  const compteHref = inPages ? 'compte.html' : 'pages/compte.html';

  container.innerHTML = `
    ${tutoBtnHTML}
    <a href="${compteHref}" class="nav-user-link" title="Mon compte">
      <span class="nav-user-avatar">
        ${user.picture
          ? `<img src="${echapperNav(user.picture)}" alt="" referrerpolicy="no-referrer">`
          : `<span>${echapperNav(initiale)}</span>`}
      </span>
      <span class="nav-user-name">${echapperNav(prenom)}</span>
    </a>
  `;
}
