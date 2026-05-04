// ══════════════════════════════════════════════════════════════
//  SUM'IT — api-client.js
//  Connexion entre le site et le backend Python FastAPI
// ══════════════════════════════════════════════════════════════

// Détection automatique : local ou production
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://sumit-web-s4lf.onrender.com';

// ── Appel API analyser-profil ───────────────────────────────
async function analyserProfilAPI(filesData, fcmax, profilType) {
  const formData = new FormData();
  filesData.forEach(f => formData.append('fichiers', f.file, f.name));
  formData.append('types',       JSON.stringify(filesData.map(f => f.type)));
  formData.append('fcmax',       fcmax);
  formData.append('profil_type', profilType);

  const res = await fetch(`${API_URL}/api/analyser-profil`, {
    method:      'POST',
    body:        formData,
    mode:        'cors',
    credentials: 'omit',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur HTTP ${res.status}`);
  }
  return await res.json();
}

// ── Appel API simuler ───────────────────────────────────────
async function simulerCourseAPI(fichierGPX, ravitosKm, profil, drainMoyH, coefficient, fcmax) {
  const formData = new FormData();
  formData.append('fichier_cible', fichierGPX, fichierGPX.name);
  formData.append('ravitos_km',    ravitosKm);
  formData.append('profil_json',   JSON.stringify(profil));
  formData.append('drain_moy_h',   drainMoyH);
  formData.append('coefficient',   coefficient);
  formData.append('fcmax',         fcmax);

  const res = await fetch(`${API_URL}/api/simuler`, {
    method:      'POST',
    body:        formData,
    mode:        'cors',
    credentials: 'omit',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur HTTP ${res.status}`);
  }
  return await res.json();
}

// ── Sauvegarde / chargement du profil ──────────────────────
function sauvegarderProfil(data) {
  try {
    // VEP globale = moyenne pondérée des vep_globale de toutes les traces
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
      timestamp:   Date.now(),
    }));
  } catch(e) {
    console.warn('Sauvegarde profil impossible:', e);
  }
}

function chargerProfil() {
  try {
    const raw = sessionStorage.getItem('sumit_profil');
    if (!raw) return null;
    const d = JSON.parse(raw);
    if (Date.now() - d.timestamp > 86400000) {
      sessionStorage.removeItem('sumit_profil');
      return null;
    }
    return d;
  } catch { return null; }
}

// ── Formatage temps ─────────────────────────────────────────
function formaterTemps(s) {
  s = Math.max(0, Math.round(s));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${h}h${String(m).padStart(2,'0')}m${String(sec).padStart(2,'0')}s`;
}
