// ══════════════════════════════════════════════════════════════
//  SUM'IT — onboarding.js v2 (non-bloquant, bas-droite)
// ══════════════════════════════════════════════════════════════

const ONBOARDING_KEY = 'sumit_onboarding_step';
const ONBOARDING_ACTIVE_KEY = 'sumit_onboarding_active';
const ONBOARDING_MIN_KEY = 'sumit_onboarding_minimized';

const ONBOARDING_STEPS = [
  {
    id: 1, page: 'any', selector: null,
    title: "👋 Bienvenue dans SUM'IT",
    text: "Tour rapide en 6 étapes pour bien démarrer.<br><br>Tu peux <strong>réduire</strong> cette fenêtre à tout moment pour explorer librement.",
    nextLabel: 'Commencer →',
    nextAction: 'goto:profil',
  },
  {
    id: 2, page: 'profil', selector: '.import-section',
    title: 'Étape 1/5 — Importe tes activités',
    text: "Importe <strong>au moins 3 GPX</strong> (idéalement 5-10) de tes sorties récentes. GPX manuel ou Strava (sélection multiple possible).<br><br>Plus tu importes, plus les prédictions sont précises.",
    nextLabel: "J'ai importé mes GPX",
    nextAction: 'next',
    checkCondition: async () => {
      try {
        const res = await listerActivites('trail');
        return res.activities && res.activities.length >= 1;
      } catch { return true; }
    },
    conditionMessage: 'Importe au moins une activité GPX',
  },
  {
    id: 3, page: 'profil', selector: '.activites-section, .activites-list',
    title: 'Étape 2/5 — Explore tes activités',
    text: "Clique sur une <strong>ligne d'activité</strong> pour voir sa <strong>carte GPS</strong> + altimétrie + KPIs détaillés.<br><br>Le crayon ✏️ te permet de renommer ou changer le type (course/entraînement/sortie).",
    nextLabel: 'Suivant →',
    nextAction: 'next',
  },
  {
    id: 4, page: 'profil', selector: '.profil-kpis, .archetype-section',
    title: 'Étape 3/5 — Découvre ton profil',
    text: "Ton profil se construit automatiquement :<br><br>• <strong>VEP globale</strong> : vitesse éq. plat<br>• <strong>Archétype</strong> parmi 8 : Grimpeur, Cabri, Diesel, Funambule, Descendeur…<br>• <strong>Score de pente</strong> : forces par terrain<br>• <strong>Évolution</strong> : graphique multi-métriques",
    nextLabel: 'Aller au simulateur →',
    nextAction: 'goto:simulateur',
  },
  {
    id: 5, page: 'simulateur', selector: '#dropzoneSim, .sidebar-sim, .sim-sidebar',
    title: 'Étape 4/6 — Simule une course',
    text: "Upload un GPX de course (UTMB, ta prochaine cible…) et lance la simulation.<br><br>L'algo prédit ton temps en tenant compte de la fatigue mécanique et de ton allure. Choisis Trail ou Rando selon le terrain.",
    nextLabel: 'Compris !',
    nextAction: 'next',
  },
  {
    id: 6, page: 'simulateur', selector: '#btnPin, .btn-pin',
    title: 'Étape 5/6 — Épingle tes simulations',
    text: "Clique sur <strong>⭐ Épingler</strong> pour sauver une simulation avant ta course.<br><br>Retrouve-les dans <strong>Mon compte</strong>, rouvre-les avec ton GPX et tes ravitos, et recalcule-les avec ton profil mis à jour.",
    nextLabel: 'Et après la course ?',
    nextAction: 'goto:bilan',
  },
  {
    id: 7, page: 'bilan', selector: '.bilan-selectors, .bilan-header',
    title: 'Étape 6/6 — Compare réel vs prédit',
    text: "Après ta course, importe-la en type <strong>🏅 Résultat</strong> dans Mon profil.<br><br>Ici, compare ta <strong>simulation</strong> à ta <strong>performance réelle</strong> : écart par ravito, ajustement du modèle, commentaire personnel. Ton profil apprend de chaque course !",
    nextLabel: 'Terminer le tour 🎉',
    nextAction: 'finish',
  },
];

function demarrerOnboarding() {
  localStorage.setItem(ONBOARDING_ACTIVE_KEY, '1');
  localStorage.setItem(ONBOARDING_KEY, '1');
  localStorage.removeItem(ONBOARDING_MIN_KEY);
  afficherEtapeOnboarding(1);
}

function stopperOnboarding() {
  localStorage.removeItem(ONBOARDING_ACTIVE_KEY);
  localStorage.removeItem(ONBOARDING_KEY);
  localStorage.removeItem(ONBOARDING_MIN_KEY);
  retirerWidget();
}

function onboardingEstActif() {
  return localStorage.getItem(ONBOARDING_ACTIVE_KEY) === '1';
}

function getOnboardingStep() {
  return parseInt(localStorage.getItem(ONBOARDING_KEY) || '0', 10);
}

function setOnboardingStep(step) {
  localStorage.setItem(ONBOARDING_KEY, String(step));
}

function estReduit() {
  return localStorage.getItem(ONBOARDING_MIN_KEY) === '1';
}

function basculerReduction() {
  if (estReduit()) {
    localStorage.removeItem(ONBOARDING_MIN_KEY);
  } else {
    localStorage.setItem(ONBOARDING_MIN_KEY, '1');
  }
  afficherEtapeOnboarding(getOnboardingStep());
}

(function reprendreOnboardingSiActif() {
  if (typeof window === 'undefined') return;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryRepriseOnboarding);
  } else {
    setTimeout(tryRepriseOnboarding, 100);
  }
})();

function tryRepriseOnboarding() {
  if (!onboardingEstActif()) return;
  const step = getOnboardingStep();
  if (step < 1 || step > ONBOARDING_STEPS.length) {
    stopperOnboarding();
    return;
  }
  setTimeout(() => afficherEtapeOnboarding(step), 600);
}

function getPageCourante() {
  const path = window.location.pathname;
  if (path.endsWith('/profil.html'))     return 'profil';
  if (path.endsWith('/simulateur.html')) return 'simulateur';
  if (path.endsWith('/bilan.html'))      return 'bilan';
  if (path.endsWith('/compte.html'))     return 'compte';
  if (path.endsWith('/avenir.html'))     return 'avenir';
  return 'home';
}

function afficherEtapeOnboarding(stepId) {
  const step = ONBOARDING_STEPS.find(s => s.id === stepId);
  if (!step) return;
  const pageCourante = getPageCourante();
  if (step.page !== 'any' && step.page !== pageCourante) return;
  setOnboardingStep(stepId);
  injecterStylesOnboarding();

  let target = null;
  if (step.selector) {
    const selectors = step.selector.split(',').map(s => s.trim());
    for (const sel of selectors) {
      target = document.querySelector(sel);
      if (target) break;
    }
  }
  afficherWidget(step, target);
}

function injecterStylesOnboarding() {
  if (document.getElementById('onboarding-styles')) return;
  const style = document.createElement('style');
  style.id = 'onboarding-styles';
  style.textContent = `
    .onb-spotlight {
      position: absolute;
      border-radius: 8px;
      border: 2px solid var(--sun);
      box-shadow: 0 0 0 4px rgba(255, 200, 87, 0.15), 0 0 20px rgba(255, 200, 87, 0.4);
      pointer-events: none;
      transition: all 0.4s ease;
      animation: onbPulse 2s ease-in-out infinite;
      z-index: 100;
    }
    @keyframes onbPulse {
      0%, 100% { box-shadow: 0 0 0 4px rgba(255, 200, 87, 0.15), 0 0 20px rgba(255, 200, 87, 0.4); }
      50%       { box-shadow: 0 0 0 6px rgba(255, 200, 87, 0.25), 0 0 35px rgba(255, 200, 87, 0.6); }
    }
    .onb-widget {
      position: fixed;
      bottom: 24px; right: 24px;
      width: 360px;
      max-width: calc(100vw - 32px);
      background: var(--bg);
      border: 1.5px solid var(--sun);
      border-radius: 12px;
      box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5), 0 0 0 4px rgba(255, 200, 87, 0.12);
      z-index: 9999;
      animation: onbSlideIn 0.4s ease;
      overflow: hidden;
    }
    @keyframes onbSlideIn {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .onb-widget-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: linear-gradient(90deg, rgba(255, 200, 87, 0.10), rgba(107, 179, 107, 0.05));
      border-bottom: 1px solid rgba(255, 200, 87, 0.2);
    }
    .onb-widget-tag {
      font-family: var(--font-display);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--sun);
    }
    .onb-widget-actions { display: flex; gap: 6px; }
    .onb-icon-btn {
      background: transparent;
      border: none;
      color: var(--text-3);
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      transition: all 0.2s;
      width: 26px; height: 26px;
      display: flex; align-items: center; justify-content: center;
    }
    .onb-icon-btn:hover { color: var(--text); background: var(--bg-3); }
    .onb-icon-btn svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2; }
    .onb-widget-body { padding: 18px 20px 20px; }
    .onb-progress { display: flex; gap: 4px; margin-bottom: 14px; }
    .onb-dot {
      flex: 1; height: 3px;
      background: var(--bg-3);
      border-radius: 2px;
      transition: background 0.3s;
    }
    .onb-dot.active { background: var(--sun); }
    .onb-dot.done   { background: var(--leaf); }
    .onb-title {
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
      letter-spacing: 0.02em;
    }
    .onb-text {
      font-size: 13px;
      color: var(--text-2);
      line-height: 1.55;
      margin-bottom: 18px;
    }
    .onb-text strong { color: var(--sun); font-weight: 600; }
    .onb-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .onb-btn {
      font-family: var(--font-display);
      font-size: 11px; font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 9px 16px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .onb-btn-skip { background: transparent; color: var(--text-3); border: none; }
    .onb-btn-skip:hover { color: var(--text-2); }
    .onb-btn-next {
      background: var(--gradient-summit);
      color: var(--bg);
      border: none;
    }
    .onb-btn-next:hover { transform: translateY(-1px); opacity: 0.95; }
    .onb-btn-next:disabled { opacity: 0.5; cursor: not-allowed; }
    .onb-warning {
      background: rgba(243, 146, 55, 0.12);
      color: var(--warning);
      border: 1px solid rgba(243, 146, 55, 0.3);
      padding: 8px 10px;
      border-radius: 4px;
      font-size: 11px;
      margin-bottom: 12px;
      display: none;
    }
    .onb-warning.show { display: block; }
    .onb-mini {
      position: fixed;
      bottom: 24px; right: 24px;
      background: var(--bg);
      border: 1.5px solid var(--sun);
      color: var(--sun);
      padding: 10px 18px;
      border-radius: 30px;
      cursor: pointer;
      font-family: var(--font-display);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      z-index: 9999;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      transition: all 0.2s;
      animation: onbSlideIn 0.4s ease;
      display: flex; align-items: center;
    }
    .onb-mini:hover { transform: translateY(-2px); }
    .onb-mini-progress {
      display: inline-block;
      width: 24px; height: 24px;
      background: var(--sun);
      color: var(--bg);
      border-radius: 50%;
      text-align: center;
      line-height: 24px;
      font-size: 10px;
      font-weight: 800;
      margin-right: 8px;
    }
  `;
  document.head.appendChild(style);
}

function retirerWidget() {
  document.querySelectorAll('#onb-widget, .onb-mini, .onb-spotlight').forEach(el => el.remove());
}

function afficherWidget(step, target) {
  retirerWidget();

  if (target) {
    const rect = target.getBoundingClientRect();
    const padding = 6;
    const spot = document.createElement('div');
    spot.className = 'onb-spotlight';
    spot.style.cssText = `top: ${rect.top + window.scrollY - padding}px; left: ${rect.left + window.scrollX - padding}px; width: ${rect.width + padding * 2}px; height: ${rect.height + padding * 2}px;`;
    document.body.appendChild(spot);

    if (rect.top < 80 || rect.bottom > window.innerHeight - 100) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => {
        const r2 = target.getBoundingClientRect();
        spot.style.top = `${r2.top + window.scrollY - padding}px`;
        spot.style.left = `${r2.left + window.scrollX - padding}px`;
      }, 500);
    }
  }

  if (estReduit()) {
    afficherMini(step);
    return;
  }

  const widget = document.createElement('div');
  widget.id = 'onb-widget';
  widget.className = 'onb-widget';

  const totalSteps = ONBOARDING_STEPS.length;
  let progressHTML = '<div class="onb-progress">';
  for (let i = 1; i <= totalSteps; i++) {
    const cls = i < step.id ? 'done' : (i === step.id ? 'active' : '');
    progressHTML += `<div class="onb-dot ${cls}"></div>`;
  }
  progressHTML += '</div>';

  widget.innerHTML = `
    <div class="onb-widget-header">
      <div class="onb-widget-tag">📘 Tutoriel · Étape ${step.id}/${totalSteps}</div>
      <div class="onb-widget-actions">
        <button class="onb-icon-btn" onclick="basculerReduction()" title="Réduire">
          <svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <button class="onb-icon-btn" onclick="stopperOnboarding()" title="Fermer">
          <svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>
    <div class="onb-widget-body">
      ${progressHTML}
      <div class="onb-title">${step.title}</div>
      <div class="onb-text">${step.text}</div>
      <div class="onb-warning" id="onb-warning"></div>
      <div class="onb-actions">
        <button class="onb-btn onb-btn-skip" onclick="stopperOnboarding()">Passer</button>
        <button class="onb-btn onb-btn-next" id="onb-btn-next">${step.nextLabel || 'Suivant →'}</button>
      </div>
    </div>
  `;

  document.body.appendChild(widget);
  document.getElementById('onb-btn-next').addEventListener('click', () => handleNextOnboarding(step));
}

function afficherMini(step) {
  const mini = document.createElement('div');
  mini.className = 'onb-mini';
  mini.onclick = basculerReduction;
  mini.innerHTML = `<span class="onb-mini-progress">${step.id}</span>Tutoriel`;
  document.body.appendChild(mini);
}

async function handleNextOnboarding(step) {
  const btn = document.getElementById('onb-btn-next');
  const warning = document.getElementById('onb-warning');

  if (step.checkCondition) {
    btn.disabled = true;
    btn.textContent = 'Vérification...';
    try {
      const ok = await step.checkCondition();
      if (!ok) {
        warning.textContent = step.conditionMessage || 'Action non terminée';
        warning.classList.add('show');
        btn.disabled = false;
        btn.textContent = step.nextLabel || 'Suivant →';
        return;
      }
    } catch (e) { /* on laisse passer */ }
  }

  switch (step.nextAction) {
    case 'goto:profil':
      setOnboardingStep(step.id + 1);
      retirerWidget();
      window.location.href = pathTo('profil');
      break;
    case 'goto:simulateur':
      setOnboardingStep(step.id + 1);
      retirerWidget();
      window.location.href = pathTo('simulateur');
      break;
    case 'goto:bilan':
      setOnboardingStep(step.id + 1);
      retirerWidget();
      window.location.href = pathTo('bilan');
      break;
    case 'finish':
      stopperOnboarding();
      setTimeout(() => alert("🎉 Bravo ! Tu maîtrises maintenant SUM'IT. Bon trail !"), 100);
      break;
    case 'next':
    default:
      const nextStep = ONBOARDING_STEPS.find(s => s.id === step.id + 1);
      if (nextStep) {
        const pageCourante = getPageCourante();
        if (nextStep.page !== 'any' && nextStep.page !== pageCourante) {
          setOnboardingStep(nextStep.id);
          retirerWidget();
          window.location.href = pathTo(nextStep.page);
        } else {
          afficherEtapeOnboarding(nextStep.id);
        }
      } else {
        stopperOnboarding();
      }
      break;
  }
}

function pathTo(page) {
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  if (page === 'home') return inPages ? '../' : '/';
  if (inPages) return `${page}.html`;
  return `/pages/${page}.html`;
}
