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

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    mode: 'cors',
  });

  if (res.status === 401) {
    // Token expiré ou invalide
    clearToken();
    throw new Error('Session expirée, reconnecte-toi');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur HTTP ${res.status}`);
  }

  return res.json();
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

async function modifierActivite(activiteId, { nom, typeSortie }) {
  const fd = new FormData();
  if (nom !== undefined) fd.append('name', nom);
  if (typeSortie !== undefined) fd.append('type_sortie', typeSortie);
  return apiFetch(`/api/activities/${activiteId}`, { method: 'PATCH', body: fd });
}

async function getActiviteDetail(activiteId) {
  return apiFetch(`/api/activities/${activiteId}`);
}

async function getEvolution(profilType = 'trail') {
  return apiFetch(`/api/evolution?profil_type=${profilType}`);
}

async function resetEvolution(profilType = 'trail') {
  return apiFetch(`/api/evolution/reset?profil_type=${profilType}`, { method: 'DELETE' });
}

async function modifierActivite(activiteId, { name, typeSortie }) {
  const fd = new FormData();
  if (name !== undefined) fd.append('name', name);
  if (typeSortie !== undefined) fd.append('type_sortie', typeSortie);
  return apiFetch(`/api/activities/${activiteId}`, { method: 'PATCH', body: fd });
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

async function simulerCourseAPI(fichierGPX, ravitosKm, profil, drainMoyH, coefficient, fcmax) {
  const formData = new FormData();
  formData.append('fichier_cible', fichierGPX, fichierGPX.name);
  formData.append('ravitos_km',    ravitosKm);
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

  // Expose explicitement toutes les fonctions appelées depuis du HTML inline (onclick)
  window.loginGoogle = loginGoogle;
  window.logout = logout;
  window.loginStrava = loginStrava;
  window.demarrerOnboarding = typeof demarrerOnboarding !== 'undefined' ? demarrerOnboarding : window.demarrerOnboarding;
}
