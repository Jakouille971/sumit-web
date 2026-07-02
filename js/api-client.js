// ══════════════════════════════════════════════════════════════
//  SUM'IT — api-client.js v2
//  Auth Google OAuth + JWT + appels API backend
// ══════════════════════════════════════════════════════════════

const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://sumit-web-s4lf.onrender.com';


// ══════════════════════════════════════════════════════════════
//  GESTION JWT (token d'authentification)
// ══════════════════════════════════════════════════════════════

const TOKEN_KEY = 'sumit_jwt';
const USER_KEY  = 'sumit_user';

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function isLoggedIn() {
  return !!getToken();
}

function getCachedUser() {
  try {
    const u = localStorage.getItem(USER_KEY);
    return u ? JSON.parse(u) : null;
  } catch { return null; }
}

function setCachedUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Capture le token depuis l'URL après redirection Google OAuth.
 * À appeler au chargement de chaque page.
 */
function capturerTokenURL() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (token) {
    setToken(token);
    // Nettoie l'URL (retire ?token=... sans recharger)
    const url = new URL(window.location);
    url.searchParams.delete('token');
    window.history.replaceState({}, '', url.toString());
    return token;
  }
  // Capture aussi les erreurs OAuth
  const authError = params.get('auth_error');
  if (authError) {
    alert(`Erreur de connexion : ${authError}`);
    const url = new URL(window.location);
    url.searchParams.delete('auth_error');
    window.history.replaceState({}, '', url.toString());
  }
  return null;
}

/**
 * Helper pour les appels API authentifiés.
 */
async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Retry automatique : le serveur Render peut être en veille (cold start ~30-60s).
  // On réessaie quelques fois sur les erreurs réseau / 502 / 503.
  const maxRetries = 6;
  let lastErr = null;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${API_URL}${path}`, { ...options, headers, mode: 'cors' });

      if (res.status === 401) {
        clearToken();
        throw new Error('Session expirée, reconnecte-toi');
      }
      // 502/503 = serveur en train de démarrer → on réessaie
      if ((res.status === 502 || res.status === 503) && attempt < maxRetries) {
        afficherBandeauReveil();
        await dormir(2500);
        continue;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Erreur HTTP ${res.status}`);
      }
      cacherBandeauReveil();
      return res.json();
    } catch (e) {
      lastErr = e;
      // Erreur d'authentification → on ne réessaie pas
      if (e.message && e.message.includes('Session expirée')) throw e;
      // Erreur réseau (serveur endormi) → on réessaie
      if (attempt < maxRetries) {
        afficherBandeauReveil();
        await dormir(2500);
        continue;
      }
    }
  }
  cacherBandeauReveil();
  throw lastErr || new Error('Le serveur ne répond pas. Réessaie dans un instant.');
}

function dormir(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Bandeau "réveil du serveur" ──────────────────────────────
let _bandeauReveilTimer = null;
let _bandeauReveilDebut = null;

function afficherBandeauReveil() {
  if (document.getElementById('sumit-reveil-banner')) return;
  _bandeauReveilDebut = Date.now();

  const banner = document.createElement('div');
  banner.id = 'sumit-reveil-banner';
  banner.innerHTML = `
    <div class="reveil-inner">
      <div class="reveil-spinner"></div>
      <div class="reveil-text">
        <strong>Réveil du serveur en cours…</strong>
        <span>La première connexion après une période d'inactivité prend ~30 à 60 secondes. Merci de patienter, ça ne durera qu'une fois.</span>
      </div>
      <div class="reveil-timer" id="sumit-reveil-timer">0s</div>
    </div>
    <div class="reveil-progress"><div class="reveil-progress-bar" id="sumit-reveil-bar"></div></div>
  `;
  injecterStylesReveil();
  document.body.appendChild(banner);

  _bandeauReveilTimer = setInterval(() => {
    const sec = Math.floor((Date.now() - _bandeauReveilDebut) / 1000);
    const t = document.getElementById('sumit-reveil-timer');
    const bar = document.getElementById('sumit-reveil-bar');
    if (t) t.textContent = `${sec}s`;
    // Barre de progression estimée sur 60s
    if (bar) bar.style.width = `${Math.min(sec / 60 * 100, 95)}%`;
  }, 1000);
}

function cacherBandeauReveil() {
  if (_bandeauReveilTimer) { clearInterval(_bandeauReveilTimer); _bandeauReveilTimer = null; }
  const b = document.getElementById('sumit-reveil-banner');
  if (b) {
    const bar = document.getElementById('sumit-reveil-bar');
    if (bar) bar.style.width = '100%';
    setTimeout(() => b.remove(), 400);
  }
}

function injecterStylesReveil() {
  if (document.getElementById('sumit-reveil-styles')) return;
  const s = document.createElement('style');
  s.id = 'sumit-reveil-styles';
  s.textContent = `
    #sumit-reveil-banner {
      position: fixed; top: 0; left: 0; right: 0;
      background: linear-gradient(90deg, rgba(255,200,87,0.14), rgba(107,179,107,0.10));
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(255,200,87,0.35);
      z-index: 99999;
      animation: reveilSlide 0.3s ease;
    }
    @keyframes reveilSlide { from { transform: translateY(-100%); } to { transform: translateY(0); } }
    .reveil-inner {
      display: flex; align-items: center; gap: 16px;
      max-width: 1000px; margin: 0 auto;
      padding: 14px 24px;
    }
    .reveil-spinner {
      width: 22px; height: 22px; flex-shrink: 0;
      border: 2.5px solid rgba(255,200,87,0.25);
      border-top-color: #FFC857;
      border-radius: 50%;
      animation: reveilSpin 0.8s linear infinite;
    }
    @keyframes reveilSpin { to { transform: rotate(360deg); } }
    .reveil-text { flex: 1; display: flex; flex-direction: column; gap: 2px; }
    .reveil-text strong {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 14px; color: #FFC857; letter-spacing: 0.02em;
    }
    .reveil-text span { font-size: 12px; color: rgba(244,241,232,0.75); line-height: 1.4; }
    .reveil-timer {
      font-family: 'Space Grotesk', monospace;
      font-size: 18px; font-weight: 700; color: #FFC857;
      min-width: 44px; text-align: right;
    }
    .reveil-progress { height: 3px; background: rgba(255,255,255,0.06); }
    .reveil-progress-bar {
      height: 100%; width: 0%;
      background: linear-gradient(90deg, #FFC857, #6BB36B);
      transition: width 1s linear;
    }
    @media (max-width: 600px) {
      .reveil-text span { display: none; }
      .reveil-inner { padding: 12px 16px; }
    }
  `;
  document.head.appendChild(s);
}

// Réveil proactif : ping /api/health au chargement (ne bloque pas).
async function reveillerServeurEnArrierePlan() {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 3000);
    const res = await fetch(`${API_URL}/api/health`, { mode: 'cors', signal: ctrl.signal });
    clearTimeout(t);
    if (res.ok) return; // serveur déjà réveillé, rien à faire
  } catch (e) {
    // Serveur endormi → on affiche le bandeau et on ping en boucle jusqu'au réveil
  }
  afficherBandeauReveil();
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(`${API_URL}/api/health`, { mode: 'cors' });
      if (res.ok) { cacherBandeauReveil(); return; }
    } catch (e) { /* encore endormi */ }
    await dormir(2500);
  }
  cacherBandeauReveil();
}


// ══════════════════════════════════════════════════════════════
//  AUTH GOOGLE
// ══════════════════════════════════════════════════════════════

function loginGoogle() {
  // Redirige vers la route backend qui démarre l'OAuth
  console.log('[SUMIT] loginGoogle appelé, redirection vers', `${API_URL}/api/auth/google/login`);
  window.location.href = `${API_URL}/api/auth/google/login`;
}

function logout() {
  clearToken();
  // Recharge la page pour reset l'état UI
  window.location.href = '/';
}

async function fetchMe() {
  const data = await apiFetch('/api/me');
  setCachedUser(data);
  return data;
}

async function updateSettings({ prenom, fcmax }) {
  const fd = new FormData();
  if (prenom !== undefined) fd.append('prenom', prenom);
  if (fcmax  !== undefined) fd.append('fcmax', fcmax);
  return apiFetch('/api/me/settings', { method: 'POST', body: fd });
}


// ══════════════════════════════════════════════════════════════
//  PROFILS (Trail / Rando)
// ══════════════════════════════════════════════════════════════

async function chargerProfilDepuisBDD(profilType) {
  try {
    return await apiFetch(`/api/profil/${profilType}`);
  } catch (e) {
    if (e.message.includes('Aucun profil')) return null;
    throw e;
  }
}

async function sauvegarderProfilEnBDD({ profilType, profilData, archetype, drainMoyH, coefficientCourse, vepGlobale, nbTraces }) {
  const fd = new FormData();
  fd.append('profil_type',        profilType);
  fd.append('profil_json',        JSON.stringify(profilData));
  fd.append('archetype_json',     JSON.stringify(archetype));
  fd.append('drain_moy_h',        drainMoyH);
  fd.append('coefficient_course', coefficientCourse);
  fd.append('vep_globale',        vepGlobale);
  fd.append('nb_traces',          nbTraces);

  return apiFetch('/api/profil/save', { method: 'POST', body: fd });
}


// ══════════════════════════════════════════════════════════════
//  ACTIVITÉS (traces individuelles stockées en BDD)
// ══════════════════════════════════════════════════════════════

async function listerActivites(profilType) {
  return apiFetch(`/api/activities?profil_type=${profilType}`);
}

async function ajouterActiviteGPX(file, typeSortie, profilType) {
  const fd = new FormData();
  fd.append('fichier',     file, file.name);
  fd.append('type_sortie', typeSortie);
  fd.append('profil_type', profilType);
  return apiFetch('/api/activities/add', { method: 'POST', body: fd });
}

async function ajouterActiviteStrava(stravaId, typeSortie, profilType, nom = '') {
  const fd = new FormData();
  fd.append('strava_id',   stravaId);
  fd.append('type_sortie', typeSortie);
  fd.append('profil_type', profilType);
  if (nom) fd.append('nom', nom);
  return apiFetch('/api/activities/add-strava', { method: 'POST', body: fd });
}

async function supprimerActivite(activiteId) {
  return apiFetch(`/api/activities/${activiteId}`, { method: 'DELETE' });
}

async function renommerActivite(activiteId, nouveauNom) {
  const fd = new FormData();
  fd.append('name', nouveauNom);
  return apiFetch(`/api/activities/${activiteId}`, { method: 'PATCH', body: fd });
}

async function modifierActivite(activiteId, { nom, name, typeSortie, dateActivity }) {
  const fd = new FormData();
  // 'nom' (FR) ou 'name' (EN) acceptés ; le backend attend 'name'
  const finalName = nom !== undefined ? nom : name;
  if (finalName !== undefined) fd.append('name', finalName);
  if (typeSortie !== undefined) fd.append('type_sortie', typeSortie);
  if (dateActivity !== undefined && dateActivity !== '') fd.append('date_activity', dateActivity);
  return apiFetch(`/api/activities/${activiteId}`, { method: 'PATCH', body: fd });
}

async function getActiviteDetail(activiteId) {
  return apiFetch(`/api/activities/${activiteId}`);
}

async function getEvolution(profilType = 'trail') {
  return apiFetch(`/api/evolution?profil_type=${profilType}`);
}

async function rebuildEvolution(profilType = 'trail') {
  return apiFetch(`/api/evolution/rebuild?profil_type=${profilType}`, { method: 'POST' });
}

async function recalculerProfil(profilType = 'trail') {
  const fd = new FormData();
  fd.append('profil_type', profilType);
  return apiFetch('/api/profil/recalculer', { method: 'POST', body: fd });
}

// ── Bilan : Réel vs Prédit (#9) ──────────────────────────────
async function getBilanCandidats() {
  return apiFetch('/api/bilan/candidats');
}

async function comparerBilan(simulationId, resultatId) {
  return apiFetch(`/api/bilan/comparer?simulation_id=${simulationId}&resultat_id=${resultatId}`);
}

async function appliquerCalibration(profilType, coefSuggere) {
  const fd = new FormData();
  fd.append('profil_type', profilType);
  fd.append('coef_suggere', coefSuggere);
  return apiFetch('/api/bilan/appliquer-calibration', { method: 'POST', body: fd });
}

async function epinglerBilan(nom, simulationId, resultatId, bilanData, commentaire = '') {
  const fd = new FormData();
  fd.append('nom', nom);
  fd.append('simulation_id', simulationId);
  fd.append('resultat_id', resultatId);
  fd.append('bilan_json', JSON.stringify(bilanData));
  if (commentaire) fd.append('commentaire', commentaire);
  return apiFetch('/api/bilan/pin', { method: 'POST', body: fd });
}

async function modifierBilan(bilanId, { commentaire, nom }) {
  const fd = new FormData();
  if (commentaire !== undefined) fd.append('commentaire', commentaire);
  if (nom !== undefined) fd.append('nom', nom);
  return apiFetch(`/api/bilan/pinned/${bilanId}`, { method: 'PATCH', body: fd });
}

async function listerBilans() {
  return apiFetch('/api/bilan/pinned');
}

async function supprimerBilan(bilanId) {
  return apiFetch(`/api/bilan/pinned/${bilanId}`, { method: 'DELETE' });
}


// ══════════════════════════════════════════════════════════════
//  STRAVA
// ══════════════════════════════════════════════════════════════

function loginStrava() {
  const token = getToken();
  if (!token) {
    alert('Connecte-toi d\'abord avec Google');
    return;
  }
  window.location.href = `${API_URL}/api/strava/login?token=${token}`;
}

async function listerActivitesStrava(perPage = 30, page = 1) {
  return apiFetch(`/api/strava/activities?per_page=${perPage}&page=${page}`);
}

async function importerActiviteStrava(activityId, typeSortie = 'entrainement') {
  const fd = new FormData();
  fd.append('type_sortie', typeSortie);
  return apiFetch(`/api/strava/import/${activityId}`, { method: 'POST', body: fd });
}

async function deconnecterStrava() {
  return apiFetch('/api/strava/disconnect', { method: 'POST' });
}


// ══════════════════════════════════════════════════════════════
//  SIMULATIONS ÉPINGLÉES
// ══════════════════════════════════════════════════════════════

async function listerSimulations() {
  return apiFetch('/api/simulations');
}

async function getSimulation(simulationId) {
  return apiFetch(`/api/simulations/${simulationId}`);
}

async function epinglerSimulation(nomCourse, profilType, simData, gpxBase64, ravitosKm) {
  const fd = new FormData();
  fd.append('nom_course',  nomCourse);
  fd.append('profil_type', profilType);
  fd.append('sim_data',    JSON.stringify(simData));
  if (gpxBase64) fd.append('gpx_base64', gpxBase64);
  if (ravitosKm) fd.append('ravitos_km', ravitosKm);
  return apiFetch('/api/simulations/pin', { method: 'POST', body: fd });
}

async function updateSimulation(simulationId, simData) {
  const fd = new FormData();
  fd.append('sim_data', JSON.stringify(simData));
  return apiFetch(`/api/simulations/${simulationId}`, { method: 'PUT', body: fd });
}

async function supprimerSimulation(simulationId) {
  return apiFetch(`/api/simulations/${simulationId}`, { method: 'DELETE' });
}


// ══════════════════════════════════════════════════════════════
//  ANCIENS APPELS (legacy : analyse profil sans BDD + simulation)
// ══════════════════════════════════════════════════════════════

async function analyserProfilAPI(filesData, fcmax, profilType) {
  const formData = new FormData();
  filesData.forEach(f => formData.append('fichiers', f.file, f.name));
  formData.append('types',       JSON.stringify(filesData.map(f => f.type)));
  formData.append('fcmax',       fcmax);
  formData.append('profil_type', profilType);

  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}/api/analyser-profil`, {
    method: 'POST', body: formData, mode: 'cors', headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur HTTP ${res.status}`);
  }
  return await res.json();
}

async function simulerCourseAPI(fichierGPX, ravitosKm, profil, drainMoyH, coefficient, fcmax, ravitosNoms, ravitosPauses) {
  const formData = new FormData();
  formData.append('fichier_cible', fichierGPX, fichierGPX.name);
  formData.append('ravitos_km',    ravitosKm);
  if (ravitosNoms && Object.keys(ravitosNoms).length > 0) {
    formData.append('ravitos_noms', JSON.stringify(ravitosNoms));
  }
  if (ravitosPauses && Object.keys(ravitosPauses).length > 0) {
    formData.append('ravitos_pauses', JSON.stringify(ravitosPauses));
  }
  formData.append('profil_json',   JSON.stringify(profil));
  formData.append('drain_moy_h',   drainMoyH);
  formData.append('coefficient',   coefficient);
  formData.append('fcmax',         fcmax);

  const res = await fetch(`${API_URL}/api/simuler`, {
    method: 'POST', body: formData, mode: 'cors',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur HTTP ${res.status}`);
  }
  return await res.json();
}


// ══════════════════════════════════════════════════════════════
//  HELPERS PROFIL (sessionStorage local pour le simulateur)
// ══════════════════════════════════════════════════════════════

function chargerProfil() {
  try {
    const data = sessionStorage.getItem('sumit_profil');
    return data ? JSON.parse(data) : null;
  } catch { return null; }
}

function sauvegarderProfil(data) {
  try {
    let vepGlobale = 0;
    if (data.traces && data.traces.length > 0) {
      vepGlobale = data.traces.reduce((s,t) => s + t.vep_globale, 0) / data.traces.length;
    }
    sessionStorage.setItem('sumit_profil', JSON.stringify({
      profil:      data.profil,
      drain_moy_h: data.drain_moy_h,
      coefficient: data.coefficient_course?.coefficient || 1.0,
      archetype:   data.archetype,
      fcmax:       data.fcmax || 193,
      prenom:      data.prenom || 'Coureur',
      nb_traces:   data.nb_traces,
      vep_globale: vepGlobale,
      profil_type: data.profil_type || 'trail',
      timestamp:   Date.now(),
    }));
  } catch(e) {
    console.warn('Sauvegarde profil impossible:', e);
  }
}

/**
 * Charge le profil depuis la BDD (si connecté) sinon depuis sessionStorage.
 * Met aussi à jour sessionStorage pour les pages qui lisent encore là.
 */
async function chargerProfilActuel(profilType = 'trail') {
  if (isLoggedIn()) {
    try {
      const p = await chargerProfilDepuisBDD(profilType);
      if (p) {
        sauvegarderProfil({
          ...p,
          profil: p.profil,
          drain_moy_h: p.drain_moy_h,
          coefficient_course: { coefficient: p.coefficient },
          fcmax: p.fcmax,
          prenom: p.prenom,
          nb_traces: p.nb_traces,
          traces: [], // pas besoin ici, vep_globale déjà calculée
          profil_type: profilType,
        });
        // Re-fix la VEP globale
        const stored = JSON.parse(sessionStorage.getItem('sumit_profil'));
        stored.vep_globale = p.vep_globale;
        sessionStorage.setItem('sumit_profil', JSON.stringify(stored));
        return stored;
      }
    } catch (e) {
      console.warn('Impossible de charger profil BDD:', e);
    }
  }
  return chargerProfil();
}

// Auto-capture du token au chargement de chaque page
if (typeof window !== 'undefined') {
  capturerTokenURL();

  // Réveil proactif du serveur Render (cold start) dès le chargement de la page
  if (typeof reveillerServeurEnArrierePlan === 'function') {
    reveillerServeurEnArrierePlan();
  }

  // Expose explicitement TOUTES les fonctions appelées depuis du HTML inline
  // ou depuis d'autres fichiers JS (nav-user, onboarding, pages)
  window.loginGoogle           = loginGoogle;
  window.logout                = logout;
  window.loginStrava           = loginStrava;
  window.fetchMe               = fetchMe;
  window.isLoggedIn            = isLoggedIn;
  window.getCachedUser         = getCachedUser;
  window.setCachedUser         = setCachedUser;
  window.clearToken            = clearToken;
  window.updateSettings        = updateSettings;
  window.deconnecterStrava     = deconnecterStrava;
  // Profils & activités
  window.listerActivites       = listerActivites;
  window.ajouterActiviteGPX    = ajouterActiviteGPX;
  window.ajouterActiviteStrava = ajouterActiviteStrava;
  window.supprimerActivite     = supprimerActivite;
  window.renommerActivite      = renommerActivite;
  window.modifierActivite      = modifierActivite;
  window.getActiviteDetail     = getActiviteDetail;
  // Strava
  window.listerActivitesStrava = listerActivitesStrava;
  // Simulations
  window.listerSimulations     = listerSimulations;
  window.getSimulation         = getSimulation;
  window.epinglerSimulation    = epinglerSimulation;
  window.updateSimulation      = updateSimulation;
  window.supprimerSimulation   = supprimerSimulation;
  // Évolution
  window.getEvolution          = getEvolution;
  window.rebuildEvolution      = rebuildEvolution;
  window.recalculerProfil      = recalculerProfil;
  // Bilan (Réel vs Prédit)
  window.getBilanCandidats     = getBilanCandidats;
  window.comparerBilan         = comparerBilan;
  window.appliquerCalibration  = appliquerCalibration;
  window.epinglerBilan         = epinglerBilan;
  window.modifierBilan         = modifierBilan;
  window.listerBilans          = listerBilans;
  window.supprimerBilan        = supprimerBilan;
  // Onboarding (au cas où)
  if (typeof demarrerOnboarding !== 'undefined') {
    window.demarrerOnboarding = demarrerOnboarding;
  }
}
