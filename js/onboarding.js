// ══════════════════════════════════════════════════════════════
//  SUM'IT — onboarding.js
//  Tour guidé en 5 étapes (Bienvenue → Import → Profil → Simu → Pin)
// ══════════════════════════════════════════════════════════════

const ONBOARDING_KEY = 'sumit_onboarding_step';
const ONBOARDING_ACTIVE_KEY = 'sumit_onboarding_active';

const ONBOARDING_STEPS = [
  {
    id: 1,
    page: 'any',
    selector: null,
    title: '👋 Bienvenue dans SUM\'IT !',
    text: `SUM'IT prédit ton temps sur n'importe quelle course de trail ou rando, en analysant tes performances passées sur GPX.<br><br>Voici un tour en 5 étapes pour bien démarrer (~2 min).`,
    nextLabel: 'Commencer →',
    nextAction: 'goto:profil',
  },
  {
    id: 2,
    page: 'profil',
    selector: '.import-section',
    title: 'Étape 1/4 — Importe tes activités',
    text: `Pour créer ton profil, importe <strong>au moins 3 GPX</strong> (idéalement 5-10) de tes sorties récentes. Tu peux uploader manuellement ou connecter Strava.<br><br>Plus tu importes, plus les prédictions sont précises.`,
    nextLabel: 'J\'ai importé mes GPX',
    nextAction: 'next',
    checkCondition: async () => {
      try {
        const res = await listerActivites('trail');
        return res.activities && res.activities.length >= 1;
      } catch { return true; }
    },
    conditionMessage: 'Importe au moins une activité GPX pour continuer',
  },
  {
    id: 3,
    page: 'profil',
    selector: '.profil-kpis, .archetype-section',
    title: 'Étape 2/4 — Découvre ton profil',
    text: `Une fois tes activités importées, ton profil se construit automatiquement :<br><br>• <strong>VEP globale</strong> : ta vitesse équivalent plat<br>• <strong>Archétype</strong> : Grimpeur, Descendeur, Tenace…<br>• <strong>Score de pente</strong> : tes forces/faiblesses par terrain`,
    nextLabel: 'Passer au simulateur →',
    nextAction: 'goto:simulateur',
  },
  {
    id: 4,
    page: 'simulateur',
    selector: '#dropzoneSim, .sidebar-sim',
    title: 'Étape 3/4 — Simule une course',
    text: `Upload un GPX de course (UTMB, Diagonale des Fous, ta prochaine cible…) et lance la simulation.<br><br>L'algo prédit ton temps en tenant compte de ton profil, de la fatigue mécanique et de ta gestion d'allure.`,
    nextLabel: 'Compris !',
    nextAction: 'next',
  },
  {
    id: 5,
    page: 'simulateur',
    selector: '#btnPin, .btn-pin',
    title: 'Étape 4/4 — Épingle tes simulations',
    text: `Pour garder tes simulations importantes (courses de la saison, objectifs), clique sur <strong>⭐ Épingler</strong>.<br><br>Tu les retrouveras dans "Mon compte" et tu pourras les rouvrir + recalculer avec ton profil mis à jour.`,
    nextLabel: 'Terminer le tour 🎉',
    nextAction: 'finish',
  },
];

function demarrerOnboarding() {
  localStorage.setItem(ONBOARDING_ACTIVE_KEY, '1');
  localStorage.setItem(ONBOARDING_KEY, '1');
  afficherEtapeOnboarding(1);
}

function stopperOnboarding() {
  localStorage.removeItem(ONBOARDING_ACTIVE_KEY);
  localStorage.removeItem(ONBOARDING_KEY);
  retirerOverlay();
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

// ── Reprise auto à chaque page ──
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

  afficherOverlay(step, target);
}

function injecterStylesOnboarding() {
  if (document.getElementById('onboarding-styles')) return;
  const style = document.createElement('style');
  style.id = 'onboarding-styles';
  style.textContent = `
    .onb-overlay {
      position: fixed; inset: 0; z-index: 9998;
      pointer-events: auto;
    }
    .onb-backdrop {
      position: absolute; inset: 0;
      background: rgba(0, 0, 0, 0.78);
    }
    .onb-spotlight {
      position: absolute;
      border-radius: 8px;
      box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.78), 0 0 0 4px var(--sun), 0 0 30px var(--sun);
      pointer-events: none;
      transition: all 0.4s ease;
      animation: onbPulse 2s ease-in-out infinite;
    }
    @keyframes onbPulse {
      0%, 100% { box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.78), 0 0 0 4px var(--sun), 0 0 30px var(--sun); }
      50%       { box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.78), 0 0 0 6px var(--sun), 0 0 50px var(--sun); }
    }
    .onb-tooltip {
      position: absolute;
      background: var(--bg);
      border: 1.5px solid var(--sun);
      border-radius: 10px;
      padding: 24px 26px;
      max-width: 440px;
      width: calc(100% - 40px);
      box-shadow: 0 12px 48px rgba(0, 0, 0, 0.7), 0 0 0 4px rgba(255, 200, 87, 0.12);
      z-index: 10000;
      animation: onbFadeIn 0.4s ease;
    }
    @keyframes onbFadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .onb-progress {
      display: flex; gap: 6px; margin-bottom: 16px;
    }
    .onb-dot {
      width: 28px; height: 4px;
      background: var(--bg-3);
      border-radius: 2px;
      transition: background 0.3s;
    }
    .onb-dot.active { background: var(--sun); }
    .onb-dot.done   { background: var(--leaf); }
    .onb-title {
      font-family: var(--font-display);
      font-size: 20px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 12px;
      letter-spacing: 0.02em;
    }
    .onb-text {
      font-size: 14px;
      color: var(--text-2);
      line-height: 1.6;
      margin-bottom: 24px;
    }
    .onb-text strong { color: var(--sun); font-weight: 600; }
    .onb-actions {
      display: flex; justify-content: space-between; align-items: center; gap: 12px;
    }
    .onb-btn {
      font-family: var(--font-display);
      font-size: 12px; font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      padding: 11px 22px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .onb-btn-skip {
      background: transparent;
      color: var(--text-3);
      border: 1px solid var(--line-2);
    }
    .onb-btn-skip:hover { color: var(--text-2); border-color: var(--text-3); }
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
      padding: 10px 12px;
      border-radius: 4px;
      font-size: 12px;
      margin-bottom: 14px;
      display: none;
    }
    .onb-warning.show { display: block; }
  `;
  document.head.appendChild(style);
}

function retirerOverlay() {
  const ov = document.getElementById('onb-overlay');
  if (ov) ov.remove();
}

function afficherOverlay(step, target) {
  retirerOverlay();

  const overlay = document.createElement('div');
  overlay.id = 'onb-overlay';
  overlay.className = 'onb-overlay';

  const backdrop = document.createElement('div');
  backdrop.className = 'onb-backdrop';
  overlay.appendChild(backdrop);

  let tooltipPos = { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };

  if (target) {
    const rect = target.getBoundingClientRect();
    const padding = 8;

    const spotlight = document.createElement('div');
    spotlight.className = 'onb-spotlight';
    spotlight.style.cssText = `
      top: ${rect.top - padding}px;
      left: ${rect.left - padding}px;
      width: ${rect.width + padding * 2}px;
      height: ${rect.height + padding * 2}px;
    `;
    overlay.appendChild(spotlight);

    if (rect.top < 80 || rect.bottom > window.innerHeight - 80) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    const tooltipHeight = 280;
    const spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow >= tooltipHeight + 30) {
      tooltipPos = { top: `${rect.bottom + 20}px`, left: '50%', transform: 'translateX(-50%)' };
    } else if (rect.top >= tooltipHeight + 30) {
      tooltipPos = { top: `${rect.top - tooltipHeight - 20}px`, left: '50%', transform: 'translateX(-50%)' };
    }
  }

  const tooltip = document.createElement('div');
  tooltip.className = 'onb-tooltip';
  Object.assign(tooltip.style, tooltipPos);

  const totalSteps = ONBOARDING_STEPS.length;
  let progressHTML = '<div class="onb-progress">';
  for (let i = 1; i <= totalSteps; i++) {
    const cls = i < step.id ? 'done' : (i === step.id ? 'active' : '');
    progressHTML += `<div class="onb-dot ${cls}"></div>`;
  }
  progressHTML += '</div>';

  tooltip.innerHTML = `
    ${progressHTML}
    <div class="onb-title">${step.title}</div>
    <div class="onb-text">${step.text}</div>
    <div class="onb-warning" id="onb-warning"></div>
    <div class="onb-actions">
      <button class="onb-btn onb-btn-skip" onclick="stopperOnboarding()">Passer le tour</button>
      <button class="onb-btn onb-btn-next" id="onb-btn-next">${step.nextLabel || 'Suivant →'}</button>
    </div>
  `;
  overlay.appendChild(tooltip);

  document.body.appendChild(overlay);

  document.getElementById('onb-btn-next').addEventListener('click', () => handleNextOnboarding(step));
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
      retirerOverlay();
      window.location.href = pathTo('profil');
      break;
    case 'goto:simulateur':
      setOnboardingStep(step.id + 1);
      retirerOverlay();
      window.location.href = pathTo('simulateur');
      break;
    case 'goto:compte':
      setOnboardingStep(step.id + 1);
      retirerOverlay();
      window.location.href = pathTo('compte');
      break;
    case 'finish':
      stopperOnboarding();
      setTimeout(() => {
        alert('🎉 Bravo ! Tu maîtrises maintenant SUM\'IT. Bon trail !');
      }, 100);
      break;
    case 'next':
    default:
      const nextStep = ONBOARDING_STEPS.find(s => s.id === step.id + 1);
      if (nextStep) {
        const pageCourante = getPageCourante();
        if (nextStep.page !== 'any' && nextStep.page !== pageCourante) {
          setOnboardingStep(nextStep.id);
          retirerOverlay();
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
