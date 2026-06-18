<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mon profil | SUM'IT</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="../css/style.css">
  <style>
    /* ── Layout ── */
    .profil-section {
      padding: 50px 80px 100px;
      max-width: 1400px;
      margin: 0 auto;
      position: relative;
      z-index: 2;
    }

    /* ── Toggle Trail/Rando ── */
    .profil-tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 32px;
      border-bottom: 1px solid var(--line);
    }
    .profil-tab {
      font-family: var(--font-display);
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-3);
      padding: 14px 28px;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      display: flex; align-items: center; gap: 8px;
    }
    .profil-tab:hover { color: var(--text-2); }
    .profil-tab.active {
      color: var(--sun);
      border-bottom-color: var(--sun);
    }

    /* ── Import section ── */
    .import-section {
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      margin-bottom: 28px;
    }
    .import-section h3 {
      font-family: var(--font-display);
      font-size: 18px;
      color: var(--text);
      margin-bottom: 4px;
      letter-spacing: 0.02em;
    }
    .import-section .desc {
      color: var(--text-3);
      font-size: 13px;
      margin-bottom: 20px;
    }
    .import-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .import-card {
      background: var(--bg);
      border: 1.5px dashed var(--line-2);
      border-radius: 6px;
      padding: 32px 24px;
      text-align: center;
      transition: all 0.2s;
      cursor: pointer;
      position: relative;
    }
    .import-card.gpx:hover {
      border-color: var(--sun);
      background: rgba(255, 200, 87, 0.03);
    }
    .import-card.strava { border-color: rgba(252, 76, 2, 0.3); }
    .import-card.strava:hover {
      border-color: #FC4C02;
      background: rgba(252, 76, 2, 0.03);
    }
    .import-card.dragover {
      border-color: var(--sun) !important;
      background: rgba(255, 200, 87, 0.08) !important;
    }
    .import-card .icon {
      width: 52px; height: 52px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 14px;
    }
    .import-card.gpx .icon { background: rgba(255, 200, 87, 0.12); }
    .import-card.gpx .icon svg { stroke: var(--sun); }
    .import-card.strava .icon { background: rgba(252, 76, 2, 0.12); }
    .import-card.strava .icon svg { stroke: #FC4C02; }
    .import-card .icon svg {
      width: 24px; height: 24px;
      fill: none; stroke-width: 1.8;
    }
    .import-card h4 {
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 4px;
      letter-spacing: 0.02em;
    }
    .import-card p {
      font-size: 12px;
      color: var(--text-3);
    }
    .strava-status {
      font-size: 11px;
      color: var(--leaf);
      margin-top: 6px;
      display: none;
    }
    .strava-status.connected { display: block; }

    /* ── Liste activités ── */
    .activites-section {
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 28px;
    }
    .activites-header {
      padding: 18px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--line);
    }
    .activites-header h3 {
      font-family: var(--font-display);
      font-size: 16px;
      color: var(--text);
      letter-spacing: 0.04em;
    }
    .activite-row {
      display: grid;
      grid-template-columns: 30px 1fr auto auto auto auto auto;
      gap: 16px;
      align-items: center;
      padding: 14px 24px;
      border-bottom: 1px solid var(--line);
      transition: background 0.2s;
    }
    .activite-row:last-child { border-bottom: none; }
    .activite-row:hover { background: var(--bg-3); }
    .source-badge {
      width: 28px; height: 28px;
      border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      font-size: 11px;
      font-family: var(--font-display);
      font-weight: 700;
    }
    .source-badge.manual { background: rgba(255, 200, 87, 0.15); color: var(--sun); }
    .source-badge.strava { background: rgba(252, 76, 2, 0.15); color: #FC4C02; }
    .activite-name {
      font-size: 13px;
      color: var(--text);
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .activite-meta {
      font-family: var(--font-display);
      font-size: 12px;
      color: var(--text-2);
      text-align: right;
      min-width: 60px;
    }
    .activite-type-tag {
      font-family: var(--font-display);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 4px 8px;
      border-radius: 3px;
      border: 1px solid var(--line-2);
    }
    .activite-type-tag.course { color: var(--sun); border-color: rgba(255, 200, 87, 0.4); background: rgba(255, 200, 87, 0.08); }
    .activite-type-tag.entrainement { color: var(--leaf); border-color: rgba(107, 179, 107, 0.4); background: rgba(107, 179, 107, 0.08); }
    .activite-type-tag.sortie { color: var(--sky); border-color: rgba(79, 163, 217, 0.4); background: rgba(79, 163, 217, 0.08); }
    .btn-delete {
      background: transparent;
      border: 1px solid var(--line);
      color: var(--text-3);
      padding: 6px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-delete:hover { border-color: var(--danger); color: var(--danger); }
    .btn-delete svg { width: 14px; height: 14px; display: block; fill: none; stroke: currentColor; stroke-width: 2; }
    .activites-empty {
      padding: 40px 24px;
      text-align: center;
      color: var(--text-3);
      font-size: 13px;
    }

    /* ── KPIs du profil ── */
    .profil-kpis {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 28px;
    }
    .profil-kpi-card {
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }
    .pk-label {
      font-family: var(--font-display);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--text-3);
      margin-bottom: 8px;
      display: flex; align-items: center;
    }
    .pk-val {
      font-family: var(--font-display);
      font-size: 32px;
      font-weight: 700;
      color: var(--text);
      line-height: 1;
    }
    .pk-val.gradient {
      background: var(--gradient-summit);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
    .pk-sub {
      font-size: 11px;
      color: var(--text-3);
      margin-top: 6px;
    }

    /* ── Archétype ── */
    .archetype-section {
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      margin-bottom: 28px;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 28px;
      align-items: center;
    }
    .archetype-icon {
      width: 80px; height: 80px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(255, 200, 87, 0.2) 0%, rgba(79, 163, 217, 0.2) 100%);
      border: 1.5px solid var(--sun);
      display: flex; align-items: center; justify-content: center;
    }
    .archetype-icon svg { width: 40px; height: 40px; fill: none; stroke: var(--sun); stroke-width: 1.5; }
    .archetype-info h3 {
      font-family: var(--font-display);
      font-size: 14px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--text-3);
      margin-bottom: 6px;
    }
    .archetype-name {
      font-family: var(--font-display);
      font-size: 28px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
      letter-spacing: 0.02em;
    }
    .archetype-desc {
      color: var(--text-2);
      font-size: 14px;
      line-height: 1.6;
    }

    /* ── Score de pente ── */
    .terrain-section {
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      margin-bottom: 28px;
    }
    .terrain-section h3 {
      font-family: var(--font-display);
      font-size: 16px;
      color: var(--text);
      margin-bottom: 4px;
      letter-spacing: 0.04em;
    }
    .terrain-section .desc {
      color: var(--text-3);
      font-size: 12px;
      margin-bottom: 24px;
    }

    /* ── Modale Strava ── */
    .modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-overlay.active { display: flex; }
    .modal-content {
      background: var(--bg);
      border: 1px solid var(--line-2);
      border-radius: 8px;
      max-width: 700px;
      width: 100%;
      max-height: 80vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .modal-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header h3 {
      font-family: var(--font-display);
      font-size: 20px;
      color: var(--text);
    }
    .modal-close {
      background: none;
      border: none;
      color: var(--text-2);
      cursor: pointer;
      font-size: 24px;
      line-height: 1;
    }
    .modal-body {
      padding: 20px 24px;
      overflow-y: auto;
      flex: 1;
    }
    .strava-activity {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 16px;
      align-items: center;
      padding: 14px;
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 6px;
      margin-bottom: 8px;
      transition: all 0.2s;
    }
    .strava-activity:hover { border-color: var(--sun); }
    .sa-name { font-size: 13px; color: var(--text); font-weight: 500; }
    .sa-meta { font-family: var(--font-display); font-size: 12px; color: var(--text-3); margin-top: 2px; }
    .sa-stats {
      font-family: var(--font-display);
      font-size: 12px;
      color: var(--text-2);
      text-align: right;
    }
    .btn-import-sa {
      background: var(--gradient-summit);
      color: var(--bg);
      font-family: var(--font-display);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 8px 14px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-import-sa:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── Modale Type Sortie (pour upload GPX ou import Strava) ── */
    .type-modal {
      max-width: 420px;
      padding: 28px;
    }
    .type-modal h3 {
      font-family: var(--font-display);
      font-size: 18px;
      color: var(--text);
      margin-bottom: 6px;
    }
    .type-modal p {
      font-size: 13px;
      color: var(--text-3);
      margin-bottom: 20px;
    }
    .type-options {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      margin-bottom: 16px;
    }
    .type-option {
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px 16px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .type-option:hover { border-color: var(--sun); }
    .type-option-name {
      font-family: var(--font-display);
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
    }
    .type-option-desc {
      font-size: 11px;
      color: var(--text-3);
      margin-top: 2px;
    }
    .type-option .tag {
      font-family: var(--font-display);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 4px 8px;
      border-radius: 3px;
      border: 1px solid;
    }

    /* ── Loading overlay ── */
    .loading-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      z-index: 2000;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      gap: 16px;
    }
    .loading-overlay.active { display: flex; }
    .spinner {
      width: 48px; height: 48px;
      border: 3px solid var(--line);
      border-top-color: var(--sun);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-text {
      color: var(--text);
      font-family: var(--font-display);
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    /* ── Login required ── */
    .login-required {
      text-align: center;
      padding: 100px 40px;
    }
    .login-required h2 {
      font-family: var(--font-display);
      font-size: 36px;
      color: var(--text);
      margin-bottom: 12px;
    }
    .login-required p {
      color: var(--text-2);
      margin-bottom: 32px;
    }

    @media (max-width: 900px) {
      .profil-section { padding: 40px 24px; }
      .import-grid { grid-template-columns: 1fr; }
      .profil-kpis { grid-template-columns: 1fr 1fr; }
      .archetype-section { grid-template-columns: 1fr; text-align: center; }
      .activite-row {
        grid-template-columns: 30px 1fr auto;
        gap: 10px;
      }
      .activite-meta:nth-child(4),
      .activite-meta:nth-child(5),
      .activite-type-tag { display: none; }
    }
  </style>
</head>
<body>

  <!-- ══ Nav ══ -->
  <nav class="nav">
    <a href="/" class="nav-logo">
      <div class="nav-logo-icon">S</div>
      <div class="nav-logo-text">
        <div class="nav-logo-name">SUM<span>'IT</span></div>
        <div class="nav-logo-sub">Plan your peaks</div>
      </div>
    </a>
    <div class="nav-links">
      <a href="/" class="nav-link">Accueil</a>
      <a href="profil.html" class="nav-link active">Mon profil</a>
      <a href="simulateur.html" class="nav-link">Simulateur</a>
      <a href="avenir.html" class="nav-link">À venir</a>
      <a href="compte.html" class="nav-link">Mon compte</a>
    </div>
  </nav>

  <!-- ══ Page hero ══ -->
  <section class="page-hero">
    <div class="page-hero-content">
      <div class="section-tag">Profil coureur</div>
      <h1>Mon <em>profil</em></h1>
      <p>Importe tes activités GPX ou Strava — ton profil se construit et se met à jour automatiquement.</p>
    </div>
  </section>

  <!-- ══ Contenu ══ -->
  <section class="profil-section" id="profilSection">
    <!-- Rempli dynamiquement -->
  </section>

  <!-- ══ Modale Strava ══ -->
  <div class="modal-overlay" id="modalStrava">
    <div class="modal-content">
      <div class="modal-header">
        <h3>📥 Importer depuis Strava</h3>
        <button class="modal-close" onclick="fermerModalStrava()">×</button>
      </div>
      <div class="modal-body" id="stravaActivitiesList">
        <p style="text-align:center;color:var(--text-3)">Chargement des activités...</p>
      </div>
    </div>
  </div>

  <!-- ══ Modale Type Sortie ══ -->
  <div class="modal-overlay" id="modalTypeSortie">
    <div class="modal-content type-modal">
      <h3>Type de sortie ?</h3>
      <p>Cette info permet de pondérer ta perf : une course vaut plus qu'un entraînement.</p>
      <div class="type-options">
        <div class="type-option" onclick="confirmerTypeSortie('course')">
          <div>
            <div class="type-option-name">🏁 Course</div>
            <div class="type-option-desc">Compétition (poids ×1.0)</div>
          </div>
          <span class="tag" style="color:var(--sun);border-color:rgba(255,200,87,0.4);background:rgba(255,200,87,0.08);">Top intensité</span>
        </div>
        <div class="type-option" onclick="confirmerTypeSortie('entrainement')">
          <div>
            <div class="type-option-name">🏃 Entraînement</div>
            <div class="type-option-desc">Sortie tempo, intervalle (poids ×0.7)</div>
          </div>
          <span class="tag" style="color:var(--leaf);border-color:rgba(107,179,107,0.4);background:rgba(107,179,107,0.08);">Régulière</span>
        </div>
        <div class="type-option" onclick="confirmerTypeSortie('sortie')">
          <div>
            <div class="type-option-name">🥾 Sortie</div>
            <div class="type-option-desc">Footing tranquille, balade (poids ×0.4)</div>
          </div>
          <span class="tag" style="color:var(--sky);border-color:rgba(79,163,217,0.4);background:rgba(79,163,217,0.08);">Détendue</span>
        </div>
      </div>
      <button class="btn-ghost" onclick="annulerTypeSortie()" style="width:100%;">Annuler</button>
    </div>
  </div>

  <!-- ══ Loading ══ -->
  <div class="loading-overlay" id="loadingOverlay">
    <div class="spinner"></div>
    <div class="loading-text" id="loadingText">Analyse en cours...</div>
  </div>

  <!-- ══ Footer ══ -->
  <footer class="footer">
    <div>
      <div class="footer-logo">SUM<span>'IT</span></div>
      <div class="footer-sub">PLAN YOUR PEAKS</div>
    </div>
    <div class="footer-copy">© 2025 SUM'IT — Beta</div>
  </footer>

  <script src="../js/api-client.js"></script>
  <script src="../js/nav-user.js"></script>
  <script>

    let currentProfilType = 'trail';
    let currentUser       = null;
    let currentProfile    = null;
    let currentActivites  = [];
    let pendingUpload     = null;  // { source: 'gpx'|'strava', file?: File, stravaId?: string, btn?: HTMLElement }

    const ARCHETYPES = {
      'Grimpeur': '🏔',
      'Descendeur': '⛷',
      'Explosif': '⚡',
      'Équilibré': '⚖',
      'Tenace': '💪',
      'Combattant': '🥊',
    };

    // ── Init ─────────────────────────────────────────────────────
    (async function init() {
      const section = document.getElementById('profilSection');

      if (!isLoggedIn()) {
        section.innerHTML = `
          <div class="login-required">
            <h2>Connecte-toi pour créer ton profil</h2>
            <p>Importe tes activités, ton profil se construit automatiquement et persiste.</p>
            <button class="btn-primary" onclick="loginGoogle()" style="font-size:14px;">
              Se connecter avec Google
            </button>
          </div>
        `;
        return;
      }

      // Gérer retour Strava
      const params = new URLSearchParams(window.location.search);
      if (params.get('strava_connected') === '1') {
        setTimeout(() => alert('✅ Compte Strava connecté !'), 200);
        cleanURL(['strava_connected']);
      }
      const stravaError = params.get('strava_error');
      if (stravaError) {
        setTimeout(() => alert(`❌ Erreur Strava : ${stravaError}`), 200);
        cleanURL(['strava_error']);
      }

      try {
        currentUser = await fetchMe();
        renderUI();
        await refreshActivites();
      } catch (e) {
        section.innerHTML = `<p style="text-align:center;color:var(--danger)">Erreur : ${e.message}</p>`;
      }
    })();

    function cleanURL(paramsToRemove) {
      const url = new URL(window.location);
      paramsToRemove.forEach(p => url.searchParams.delete(p));
      window.history.replaceState({}, '', url.toString());
    }

    // ── Render principal ────────────────────────────────────────
    function renderUI() {
      const profileTrail = currentUser.profiles.find(p => p.type === 'trail');
      const profileRando = currentUser.profiles.find(p => p.type === 'rando');
      currentProfile = currentProfilType === 'trail' ? profileTrail : profileRando;

      const section = document.getElementById('profilSection');
      section.innerHTML = `
        <!-- Tabs -->
        <div class="profil-tabs">
          <div class="profil-tab ${currentProfilType==='trail'?'active':''}" onclick="switchTab('trail')">
            🏃 Trail / Course
          </div>
          <div class="profil-tab ${currentProfilType==='rando'?'active':''}" onclick="switchTab('rando')">
            🥾 Randonnée
          </div>
        </div>

        <!-- Import section -->
        <div class="import-section">
          <h3>➕ Ajouter une activité ${currentProfilType==='trail' ? 'trail/course' : 'randonnée'}</h3>
          <p class="desc">Chaque ajout met à jour automatiquement ton profil. Tu peux supprimer une activité à tout moment.</p>
          <div class="import-grid">
            <div class="import-card gpx" id="gpxDropzone" onclick="document.getElementById('gpxFileInput').click()">
              <div class="icon">
                <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
              </div>
              <h4>Import GPX</h4>
              <p>Glisse-dépose ou clique pour uploader</p>
              <input type="file" id="gpxFileInput" accept=".gpx" style="display:none" onchange="handleGPXSelected(event)">
            </div>
            <div class="import-card strava" onclick="handleStravaClick()">
              <div class="icon">
                <svg viewBox="0 0 24 24"><path d="M12 1l9 16-9 6-9-6 9-16z"/></svg>
              </div>
              <h4>Import Strava</h4>
              <p>${currentUser.strava_connected ? 'Choisir parmi tes activités Strava' : 'Connecter ton compte Strava'}</p>
              <p class="strava-status ${currentUser.strava_connected?'connected':''}">✓ Strava connecté</p>
            </div>
          </div>
        </div>

        <!-- Liste activités -->
        <div class="activites-section">
          <div class="activites-header">
            <h3>📂 Mes activités ${currentProfilType==='trail' ? 'trail' : 'randonnée'}</h3>
            <span style="color:var(--text-3);font-size:12px;font-family:var(--font-display);" id="activitesCount">— activités</span>
          </div>
          <div id="activitesContainer">
            <div class="activites-empty">Chargement...</div>
          </div>
        </div>

        <!-- Profil affiché (si existe) -->
        ${currentProfile ? renderProfileDetails() : `
          <div style="text-align:center;padding:40px;background:var(--bg-2);border:1px solid var(--line);border-radius:8px;">
            <p style="color:var(--text-2);font-size:14px;">Ton profil ${currentProfilType==='trail'?'trail':'rando'} se construira automatiquement après ton premier import.</p>
          </div>
        `}
      `;

      // Drag & drop sur la dropzone
      attachDragDrop();
    }

    function renderProfileDetails() {
      const p = currentProfile;
      const arch = p.archetype || {};
      const archIcon = ARCHETYPES[arch.nom] || '🏃';
      const profilData = p.profil_data || {};

      return `
        <!-- KPIs principaux -->
        <div class="profil-kpis">
          <div class="profil-kpi-card">
            <div class="pk-label">VEP Globale</div>
            <div class="pk-val gradient">${p.vep_globale.toFixed(1)}</div>
            <div class="pk-sub">km/h éq. plat</div>
          </div>
          <div class="profil-kpi-card">
            <div class="pk-label">Drain énergie</div>
            <div class="pk-val">${(p.drain_moy_h*100).toFixed(1)}</div>
            <div class="pk-sub">% batterie / heure</div>
          </div>
          <div class="profil-kpi-card">
            <div class="pk-label">Activités</div>
            <div class="pk-val">${p.nb_traces}</div>
            <div class="pk-sub">analysées</div>
          </div>
          <div class="profil-kpi-card">
            <div class="pk-label">Coef course</div>
            <div class="pk-val">×${p.coefficient_course.toFixed(2)}</div>
            <div class="pk-sub">vs entraînement</div>
          </div>
        </div>

        <!-- Archétype -->
        <div class="archetype-section">
          <div class="archetype-icon">
            <span style="font-size:38px;">${archIcon}</span>
          </div>
          <div class="archetype-info">
            <h3>Ton archétype</h3>
            <div class="archetype-name">${arch.nom || 'Combattant'}</div>
            <div class="archetype-desc">${arch.desc || 'Polyvalent, régulier sur tous les terrains.'}</div>
          </div>
        </div>

        <!-- Score de pente -->
        <div class="terrain-section">
          <h3>Score de pente</h3>
          <p class="desc">Écart de performance par type de terrain par rapport à ton allure sur le plat (référence 0%).</p>
          ${renderScorePente(profilData)}
        </div>
      `;
    }

    function renderScorePente(profilData) {
      const ordreT = ['montee_raide','montee_soutenue','montee_douce','plat','descente_douce','descente_soutenue','descente_raide'];
      const labels = {
        montee_raide: 'Montée raide',
        montee_soutenue: 'Montée soutenue',
        montee_douce: 'Montée douce',
        plat: 'Plat (référence)',
        descente_douce: 'Descente douce',
        descente_soutenue: 'Descente soutenue',
        descente_raide: 'Descente raide',
      };

      let html = '';
      ordreT.forEach(t => {
        const data = profilData[t];
        if (!data) return;
        const ecart = data.ecart_plat_pct || 0;
        const isPlat = (t === 'plat');
        const widthPct = Math.min(50, Math.abs(ecart));

        let fillClass = 'positive';
        let valClass = 'positive';
        if (isPlat) { valClass = 'neutral'; }
        else if (ecart < 0) { fillClass = 'negative'; valClass = 'negative'; }

        const display = isPlat ? '0%' : `${ecart > 0 ? '+' : ''}${ecart.toFixed(1)}%`;

        html += `
          <div class="score-bar">
            <div class="score-label">${labels[t]}</div>
            <div class="score-track">
              ${isPlat ? '' : `<div class="score-fill ${fillClass}" style="width:${widthPct}%;"></div>`}
            </div>
            <div class="score-val ${valClass}">${display}</div>
          </div>
        `;
      });
      return html;
    }

    // ── Tabs ────────────────────────────────────────────────────
    async function switchTab(type) {
      currentProfilType = type;
      renderUI();
      await refreshActivites();
    }

    // ── Activités : chargement & affichage ──────────────────────
    async function refreshActivites() {
      try {
        const res = await listerActivites(currentProfilType);
        currentActivites = res.activities || [];
        renderActivites();
      } catch (e) {
        document.getElementById('activitesContainer').innerHTML =
          `<div class="activites-empty">Erreur : ${e.message}</div>`;
      }
    }

    function renderActivites() {
      const cont = document.getElementById('activitesContainer');
      const count = document.getElementById('activitesCount');
      count.textContent = `${currentActivites.length} activité${currentActivites.length>1?'s':''}`;

      if (currentActivites.length === 0) {
        cont.innerHTML = `<div class="activites-empty">Aucune activité pour ce profil. Importe ta première activité ci-dessus 👆</div>`;
        return;
      }

      cont.innerHTML = currentActivites.map(a => {
        const dureeMin = Math.round(a.duree_s / 60);
        const dureeFmt = dureeMin >= 60 ? `${Math.floor(dureeMin/60)}h${String(dureeMin%60).padStart(2,'0')}` : `${dureeMin}min`;
        const date = a.date ? new Date(a.date).toLocaleDateString('fr-FR', {day:'2-digit', month:'short', year:'2-digit'}) : '—';
        return `
          <div class="activite-row">
            <div class="source-badge ${a.source}" title="${a.source === 'strava' ? 'Strava' : 'Import manuel'}">
              ${a.source === 'strava' ? 'S' : '📁'}
            </div>
            <div>
              <div class="activite-name">${a.name || 'Sans nom'}</div>
              <div style="font-size:11px;color:var(--text-3)">${date}</div>
            </div>
            <span class="activite-type-tag ${a.type_sortie}">${a.type_sortie}</span>
            <div class="activite-meta">${a.dist_km.toFixed(1)} km</div>
            <div class="activite-meta">${Math.round(a.dplus_m)} m D+</div>
            <div class="activite-meta">${dureeFmt}</div>
            <button class="btn-delete" onclick="deleteActivite(${a.id})" title="Supprimer">
              <svg viewBox="0 0 24 24"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        `;
      }).join('');
    }

    async function deleteActivite(id) {
      if (!confirm('Supprimer cette activité ? Ton profil sera recalculé automatiquement.')) return;
      showLoading('Recalcul du profil...');
      try {
        await supprimerActivite(id);
        await rechargerProfilEtActivites();
      } catch (e) {
        alert('Erreur : ' + e.message);
      } finally {
        hideLoading();
      }
    }

    // ── Drag & Drop GPX ─────────────────────────────────────────
    function attachDragDrop() {
      const dz = document.getElementById('gpxDropzone');
      if (!dz) return;
      ['dragenter','dragover'].forEach(evt => {
        dz.addEventListener(evt, e => { e.preventDefault(); dz.classList.add('dragover'); });
      });
      ['dragleave','drop'].forEach(evt => {
        dz.addEventListener(evt, e => { e.preventDefault(); dz.classList.remove('dragover'); });
      });
      dz.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].name.toLowerCase().endsWith('.gpx')) {
          ouvrirModalTypeSortie({ source: 'gpx', file: files[0] });
        }
      });
    }

    function handleGPXSelected(event) {
      const file = event.target.files[0];
      if (!file) return;
      ouvrirModalTypeSortie({ source: 'gpx', file });
      event.target.value = '';  // reset input
    }

    // ── Type sortie (modale) ────────────────────────────────────
    function ouvrirModalTypeSortie(upload) {
      pendingUpload = upload;
      document.getElementById('modalTypeSortie').classList.add('active');
    }

    function annulerTypeSortie() {
      pendingUpload = null;
      document.getElementById('modalTypeSortie').classList.remove('active');
    }

    async function confirmerTypeSortie(typeSortie) {
      document.getElementById('modalTypeSortie').classList.remove('active');
      if (!pendingUpload) return;

      showLoading('Analyse en cours, ne quitte pas la page...');

      try {
        if (pendingUpload.source === 'gpx') {
          await ajouterActiviteGPX(pendingUpload.file, typeSortie, currentProfilType);
        } else if (pendingUpload.source === 'strava') {
          await ajouterActiviteStrava(pendingUpload.stravaId, typeSortie, currentProfilType);
          // Reset bouton modal Strava
          if (pendingUpload.btn) {
            pendingUpload.btn.textContent = '✓ Importée';
            pendingUpload.btn.disabled = true;
          }
        }

        await rechargerProfilEtActivites();

      } catch (e) {
        alert('Erreur : ' + e.message);
        if (pendingUpload.btn) {
          pendingUpload.btn.disabled = false;
          pendingUpload.btn.textContent = 'Importer';
        }
      } finally {
        pendingUpload = null;
        hideLoading();
      }
    }

    async function rechargerProfilEtActivites() {
      currentUser = await fetchMe();
      renderUI();
      await refreshActivites();
    }

    // ── Strava ──────────────────────────────────────────────────
    async function handleStravaClick() {
      if (!currentUser.strava_connected) {
        if (confirm("Tu vas être redirigé vers Strava pour autoriser SUM'IT à lire tes activités. Continuer ?")) {
          loginStrava();
        }
        return;
      }
      await ouvrirModalStrava();
    }

    async function ouvrirModalStrava() {
      document.getElementById('modalStrava').classList.add('active');
      const list = document.getElementById('stravaActivitiesList');
      list.innerHTML = `<p style="text-align:center;color:var(--text-3)">Chargement des activités Strava...</p>`;

      try {
        const res = await listerActivitesStrava(50);
        const activities = res.activities || [];

        if (activities.length === 0) {
          list.innerHTML = `<p style="text-align:center;color:var(--text-3)">Aucune activité de course/rando trouvée sur Strava.</p>`;
          return;
        }

        const dejaImportes = new Set(currentActivites.filter(a => a.source === 'strava').map(a => a.external_id));

        list.innerHTML = activities.map(a => {
          const date = new Date(a.date).toLocaleDateString('fr-FR', {day:'2-digit', month:'short', year:'2-digit'});
          const dureeMin = Math.round(a.duree_s / 60);
          const dureeFmt = dureeMin >= 60 ? `${Math.floor(dureeMin/60)}h${String(dureeMin%60).padStart(2,'0')}` : `${dureeMin}min`;
          const isImported = dejaImportes.has(String(a.id));
          return `
            <div class="strava-activity">
              <div>
                <div class="sa-name">${a.name}</div>
                <div class="sa-meta">${a.type} · ${date}</div>
              </div>
              <div class="sa-stats">
                ${a.distance_km.toFixed(1)} km · ${Math.round(a.dplus_m)}m D+<br>
                <span style="color:var(--text-3)">${dureeFmt}</span>
              </div>
              <button class="btn-import-sa" onclick="declencherImportStrava('${a.id}', this)" ${isImported ? 'disabled' : ''}>
                ${isImported ? '✓ Importée' : 'Importer'}
              </button>
            </div>
          `;
        }).join('');
      } catch (e) {
        list.innerHTML = `<p style="color:var(--danger);text-align:center;">Erreur : ${e.message}</p>`;
      }
    }

    function fermerModalStrava() {
      document.getElementById('modalStrava').classList.remove('active');
    }

    function declencherImportStrava(stravaId, btn) {
      btn.disabled = true;
      btn.textContent = '...';
      fermerModalStrava();
      ouvrirModalTypeSortie({ source: 'strava', stravaId, btn });
    }

    // ── Loading overlay ────────────────────────────────────────
    function showLoading(text) {
      document.getElementById('loadingText').textContent = text || 'Chargement...';
      document.getElementById('loadingOverlay').classList.add('active');
    }
    function hideLoading() {
      document.getElementById('loadingOverlay').classList.remove('active');
    }

  </script>
</body>
</html>
