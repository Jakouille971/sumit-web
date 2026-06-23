// ══════════════════════════════════════════════════════════════
//  SUM'IT — nav-user.js v2
//  Garantit l'uniformité de la nav sur toutes les pages :
//   - Liens : Accueil, Mon profil, Simulateur, À venir, Mon compte
//   - Bouton "Se connecter" OU avatar utilisateur
// ══════════════════════════════════════════════════════════════

(async function initNavUniforme() {
  const nav = document.querySelector('.nav');
  if (!nav) return;

  injecterStylesNav();
  uniformiserLiens(nav);
  await uniformiserUserSlot(nav);
  creerBurgerMenu(nav);
})();

// ── Menu hamburger mobile ───────────────────────────────────────
function creerBurgerMenu(nav) {
  // Évite les doublons
  if (nav.querySelector('.nav-burger')) return;

  const burger = document.createElement('button');
  burger.className = 'nav-burger';
  burger.setAttribute('aria-label', 'Menu');
  burger.innerHTML = '<span></span><span></span><span></span>';

  burger.addEventListener('click', () => {
    const links = nav.querySelector('.nav-links');
    burger.classList.toggle('open');
    if (links) links.classList.toggle('mobile-open');
  });

  // Insérer le burger juste avant le conteneur user (ou à la fin)
  const userContainer = nav.querySelector('#nav-user-container');
  if (userContainer) {
    nav.insertBefore(burger, userContainer);
  } else {
    nav.appendChild(burger);
  }

  // Fermer le menu quand on clique sur un lien
  const links = nav.querySelector('.nav-links');
  if (links) {
    links.addEventListener('click', (e) => {
      if (e.target.classList.contains('nav-link')) {
        burger.classList.remove('open');
        links.classList.remove('mobile-open');
      }
    });
  }
}

// ── 1. Uniformiser les liens de navigation ─────────────────────
function uniformiserLiens(nav) {
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  const prefix = inPages ? '' : 'pages/';

  // Ordre voulu : Accueil, Mon profil, Simulateur, Mon compte, À venir
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
    const activeClass = lien.id === currentId ? ' active' : '';
    return `<a href="${lien.href}" class="nav-link${activeClass}">${lien.label}</a>`;
  }).join('');
}

// ── 2. Slot utilisateur (login button OU avatar) + tutoriel ─────
async function uniformiserUserSlot(nav) {
  let container = document.getElementById('nav-user-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'nav-user-container';
    container.style.cssText = 'display:flex;align-items:center;gap:10px;margin-left:14px;';
    const oldCta = nav.querySelector('.nav-cta');
    if (oldCta) oldCta.remove();
    nav.appendChild(container);
  }

  // Affichage IMMÉDIAT (synchrone) basé sur l'état local (token + cache)
  // On ne bloque jamais sur fetchMe() qui peut prendre 30s si Render dort
  const tutoBtnHTML = construireBtnTutoriel();
  const tokenPresent = (typeof isLoggedIn === 'function') && isLoggedIn();
  const cachedUser = (typeof getCachedUser === 'function') ? getCachedUser() : null;

  if (tokenPresent && cachedUser) {
    // On affiche déjà l'avatar avec les infos en cache (rapide)
    renderLoggedIn(container, cachedUser, tutoBtnHTML);
  } else if (tokenPresent) {
    // Token mais pas de cache : on affiche un avatar générique en attendant
    renderLoggedIn(container, { prenom: 'Coureur', email: '' }, tutoBtnHTML);
  } else {
    // Pas connecté → bouton de connexion direct
    renderLoggedOut(container, tutoBtnHTML);
  }

  // Enrichissement async en arrière-plan (sans bloquer)
  if (tokenPresent && typeof fetchMe === 'function') {
    fetchMe().then(user => {
      // Mise à jour du DOM avec les vraies infos
      renderLoggedIn(container, user, tutoBtnHTML);
    }).catch(e => {
      // Si le token est invalide (401), on bascule en mode déconnecté
      if (e && e.message && e.message.includes('expirée')) {
        if (typeof clearToken === 'function') clearToken();
        renderLoggedOut(container, tutoBtnHTML);
      }
      // Si c'est juste un timeout réseau / Render down, on garde l'UI actuelle
      // (l'utilisateur peut toujours utiliser l'app en mode offline-cache)
    });
  }
}

function construireBtnTutoriel() {
  // Toujours afficher le bouton tutoriel, même si onboarding.js pas encore chargé
  return `
    <button class="nav-tuto-btn" onclick="if(typeof demarrerOnboarding==='function'){demarrerOnboarding()}else{alert('Tutoriel en cours de chargement...');}" title="Voir le tutoriel">
      <svg viewBox="0 0 24 24" width="16" height="16">
        <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 14l9-5-9-5-9 5 9 5z"/>
        <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 14l6.16-3.422a12.083 12.083 0 0 1 .665 6.479A11.952 11.952 0 0 0 12 20.055a11.952 11.952 0 0 0-6.824-2.998 12.078 12.078 0 0 1 .665-6.479L12 14z"/>
      </svg>
      <span>Tutoriel</span>
    </button>
  `;
}

function renderLoggedOut(container, tutoBtnHTML = '') {
  // Fallback de sécurité : construit l'URL même si loginGoogle() n'est pas dispo
  const API_BASE = (typeof API_URL !== 'undefined') ? API_URL :
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8000'
      : 'https://sumit-web-s4lf.onrender.com');

  container.innerHTML = `
    ${tutoBtnHTML}
    <a href="${API_BASE}/api/auth/google/login" class="nav-login-btn" style="text-decoration:none;">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:8px;">
        <path fill="currentColor" d="M21.35 11.1h-9.17v2.73h6.51c-.33 3.81-3.5 5.44-6.5 5.44C8.36 19.27 5 16.25 5 12c0-4.1 3.2-7.27 7.2-7.27 3.09 0 4.9 1.97 4.9 1.97L19 4.72S16.56 2 12.1 2C6.42 2 2.03 6.8 2.03 12c0 5.05 4.13 10 10.22 10 5.35 0 9.25-3.67 9.25-9.09 0-1.15-.15-1.81-.15-1.81z"/>
      </svg>
      Se connecter
    </a>
  `;
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
      <div class="nav-user-avatar">
        ${user.picture
          ? `<img src="${user.picture}" alt="${prenom}">`
          : `<span>${initiale}</span>`}
      </div>
      <span class="nav-user-name">${prenom}</span>
    </a>
  `;
}

// ── 3. Styles ──────────────────────────────────────────────────
function injecterStylesNav() {
  if (document.getElementById('nav-user-styles')) return;
  const style = document.createElement('style');
  style.id = 'nav-user-styles';
  style.textContent = `
    .nav-login-btn {
      background: var(--gradient-summit);
      color: var(--bg);
      font-family: var(--font-display);
      font-size: 12px; font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      padding: 10px 22px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      display: inline-flex; align-items: center;
      transition: transform 0.15s, opacity 0.2s;
    }
    .nav-login-btn:hover { transform: translateY(-1px); opacity: 0.95; }

    .nav-tuto-btn {
      background: transparent;
      color: var(--text-2);
      font-family: var(--font-display);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 8px 14px;
      border: 1px solid var(--line);
      border-radius: 4px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .nav-tuto-btn:hover {
      color: var(--sun);
      border-color: var(--sun);
      background: rgba(255, 200, 87, 0.06);
    }
    .nav-tuto-btn svg { stroke: currentColor; }
    .nav-user-link {
      display: inline-flex; align-items: center; gap: 10px;
      padding: 5px 14px 5px 5px;
      border-radius: 30px;
      border: 1px solid var(--line);
      background: var(--bg-2);
      text-decoration: none;
      color: var(--text);
      transition: all 0.2s;
    }
    .nav-user-link:hover {
      border-color: var(--sun);
      background: var(--bg-3);
    }
    .nav-user-avatar {
      width: 30px; height: 30px;
      border-radius: 50%;
      background: var(--gradient-summit);
      display: flex; align-items: center; justify-content: center;
      font-family: var(--font-display);
      font-size: 13px; font-weight: 700;
      color: var(--bg);
      overflow: hidden;
      flex-shrink: 0;
    }
    .nav-user-avatar img { width: 100%; height: 100%; object-fit: cover; }
    .nav-user-name {
      font-family: var(--font-display);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
    }
  `;
  document.head.appendChild(style);
}
