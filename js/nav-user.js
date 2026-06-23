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
})();

// ── 1. Uniformiser les liens de navigation ─────────────────────
function uniformiserLiens(nav) {
  // Détermine si on est en pages/ ou à la racine
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  const prefix = inPages ? '' : 'pages/';

  // Liens attendus, dans l'ordre
  const LIENS_ATTENDUS = [
    { label: 'Accueil',    href: inPages ? '../' : '/',         id: 'home' },
    { label: 'Mon profil', href: `${prefix}profil.html`,        id: 'profil' },
    { label: 'Simulateur', href: `${prefix}simulateur.html`,    id: 'simulateur' },
    { label: 'À venir',    href: `${prefix}avenir.html`,        id: 'avenir' },
    { label: 'Mon compte', href: `${prefix}compte.html`,        id: 'compte' },
  ];

  // Page active
  const currentId =
    path.endsWith('profil.html')     ? 'profil' :
    path.endsWith('simulateur.html') ? 'simulateur' :
    path.endsWith('avenir.html')     ? 'avenir' :
    path.endsWith('compte.html')     ? 'compte' :
    'home';

  // Trouver ou créer le conteneur .nav-links
  let navLinks = nav.querySelector('.nav-links');
  if (!navLinks) {
    navLinks = document.createElement('div');
    navLinks.className = 'nav-links';
    nav.appendChild(navLinks);
  }

  // Reconstruire complètement les liens dans le bon ordre
  navLinks.innerHTML = LIENS_ATTENDUS.map(lien => {
    const activeClass = lien.id === currentId ? ' active' : '';
    return `<a href="${lien.href}" class="nav-link${activeClass}">${lien.label}</a>`;
  }).join('');
}

// ── 2. Slot utilisateur (login button OU avatar) ───────────────
async function uniformiserUserSlot(nav) {
  let container = document.getElementById('nav-user-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'nav-user-container';
    container.style.cssText = 'display:flex;align-items:center;gap:14px;margin-left:14px;';
    const oldCta = nav.querySelector('.nav-cta');
    if (oldCta) oldCta.remove();
    nav.appendChild(container);
  }

  if (typeof isLoggedIn === 'function' && isLoggedIn()) {
    let user = (typeof getCachedUser === 'function') ? getCachedUser() : null;
    try {
      user = await fetchMe();
    } catch (e) {
      if (typeof clearToken === 'function') clearToken();
      renderLoggedOut(container);
      return;
    }
    renderLoggedIn(container, user);
  } else {
    renderLoggedOut(container);
  }
}

function renderLoggedOut(container) {
  container.innerHTML = `
    <button class="nav-login-btn" onclick="loginGoogle()">
      <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right:8px;">
        <path fill="currentColor" d="M21.35 11.1h-9.17v2.73h6.51c-.33 3.81-3.5 5.44-6.5 5.44C8.36 19.27 5 16.25 5 12c0-4.1 3.2-7.27 7.2-7.27 3.09 0 4.9 1.97 4.9 1.97L19 4.72S16.56 2 12.1 2C6.42 2 2.03 6.8 2.03 12c0 5.05 4.13 10 10.22 10 5.35 0 9.25-3.67 9.25-9.09 0-1.15-.15-1.81-.15-1.81z"/>
      </svg>
      Se connecter
    </button>
  `;
}

function renderLoggedIn(container, user) {
  const prenom = user.prenom || user.name?.split(' ')[0] || 'Coureur';
  const initiale = prenom[0]?.toUpperCase() || 'C';
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  const compteHref = inPages ? 'compte.html' : 'pages/compte.html';

  container.innerHTML = `
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
