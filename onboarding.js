// ══════════════════════════════════════════════════════════════
//  SUM'IT — onboarding.js v3
//  Tutoriel non bloquant : carte flottante en bas à droite (feuille en bas
//  sur téléphone), repère sur l'élément concerné, reprise d'une page à l'autre.
// ══════════════════════════════════════════════════════════════

const ONBOARDING_KEY = 'sumit_onboarding_step';
const ONBOARDING_ACTIVE_KEY = 'sumit_onboarding_active';
const ONBOARDING_MIN_KEY = 'sumit_onboarding_minimized';

const ONBOARDING_STEPS = [
  {
    id: 1, page: 'any', selector: null,
    title: "Bienvenue dans SUM'IT",
    text: "Six étapes pour passer de tes traces GPX à ton plan de course. Tu peux <strong>réduire</strong> cette fenêtre à tout moment pour explorer librement.",
    nextLabel: 'Commencer',
    nextAction: 'goto:profil',
  },
  {
    id: 2, page: 'profil', selector: '.import-section',
    title: 'Importe tes activités',
    text: "Connecte-toi avec Google, puis importe <strong>au moins 3 traces GPX</strong> de tes sorties récentes (5 à 10, c'est idéal), en fichier ou depuis Strava. Plus tu en importes, plus la prédiction est juste.",
    nextLabel: "J'ai importé mes traces",
    nextAction: 'next',
    checkCondition: async () => {
      try {
        const res = await listerActivites('trail');
        return res.activities && res.activities.length >= 1;
      } catch { return true; }
    },
    conditionMessage: "Importe au moins une activité pour continuer.",
  },
  {
    id: 3, page: 'profil', selector: '.activites-section',
    title: 'Explore tes activités',
    text: "Clique sur une activité pour voir sa <strong>carte</strong>, son profil altimétrique et ses chiffres. Le crayon permet de la renommer ou de changer son type : course, entraînement, sortie.",
    nextLabel: 'Suivant',
    nextAction: 'next',
  },
  {
    id: 4, page: 'profil', selector: '.archetype-section, .profil-kpis',
    title: 'Découvre ton profil',
    text: "Il se construit tout seul : ta <strong>VEP</strong> (vitesse équivalente plat), ton <strong>archétype</strong> parmi huit, ton score de pente terrain par terrain et ton évolution.",
    nextLabel: 'Aller au simulateur',
    nextAction: 'goto:simulateur',
  },
  {
    id: 5, page: 'simulateur', selector: '.sim-sidebar, #dropzoneSim',
    title: 'Simule une course',
    text: "Dépose le GPX de ta course objectif, ajoute tes ravitos et lance la simulation. Pas de course sous la main ? Essaie la <strong>démo CCC</strong>.",
    nextLabel: 'Suivant',
    nextAction: 'next',
  },
  {
    id: 6, page: 'simulateur', selector: '#btnPin, .btn-pin',
    title: 'Épingle ta simulation',
    text: "Une fois la simulation lancée, le bouton <strong>Épingler</strong> la garde dans Mon compte. Tu pourras la rouvrir avec ton GPX et tes ravitos, et la recalculer quand ton profil progresse.",
    nextLabel: 'Et après la course ?',
    nextAction: 'goto:bilan',
  },
  {
    id: 7, page: 'bilan', selector: '.bilan-selectors',
    title: 'Compare réel et prédit',
    text: "Après ta course, importe-la dans Mon profil avec le type <strong>Résultat</strong>. Ici, compare-la à ta simulation : écart à chaque ravito, recalibrage du modèle, notes personnelles.",
    nextLabel: 'Terminer le tour',
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
  const focusCible = estReduit() ? document.querySelector('.onb-mini') : document.getElementById('onb-btn-next');
  if (focusCible) focusCible.focus({ preventScroll: true });
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
      const el = document.querySelector(sel);
      // On ignore les éléments masqués (pas de repère à 0,0)
      if (el && el.getClientRects().length && el.getBoundingClientRect().width > 0) { target = el; break; }
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
      border-radius: 10px;
      outline: 2px solid #1E5FD8;
      outline-offset: 0;
      box-shadow: 0 0 0 6px rgba(30, 95, 216, 0.14);
      pointer-events: none;
      z-index: 90;
      animation: onbSpot 1.6s cubic-bezier(0.23, 1, 0.32, 1) 2;
    }
    @keyframes onbSpot {
      0%   { box-shadow: 0 0 0 0 rgba(30, 95, 216, 0.30); }
      70%  { box-shadow: 0 0 0 10px rgba(30, 95, 216, 0); }
      100% { box-shadow: 0 0 0 6px rgba(30, 95, 216, 0.14); }
    }
    .onb-widget {
      position: fixed;
      right: max(24px, env(safe-area-inset-right));
      bottom: max(24px, env(safe-area-inset-bottom));
      width: 360px;
      max-width: calc(100vw - 32px);
      background: #FFFFFF;
      color: #0E1116;
      border: 1px solid #E4E7EB;
      border-radius: 12px;
      box-shadow: 0 1px 2px rgba(14, 17, 22, 0.06), 0 12px 32px rgba(14, 17, 22, 0.14);
      z-index: 9999;
      font-family: 'Sora', system-ui, sans-serif;
      transform-origin: bottom right;
      animation: onbIn 260ms cubic-bezier(0.23, 1, 0.32, 1);
    }
    @keyframes onbIn {
      from { opacity: 0; transform: translateY(8px) scale(0.98); }
    }
    .onb-widget-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      padding: 12px 12px 0 18px;
    }
    .onb-widget-tag { font-size: 13px; font-weight: 600; color: #5C6370; font-variant-numeric: tabular-nums; }
    .onb-widget-actions { display: flex; gap: 2px; }
    .onb-icon-btn {
      width: 32px; height: 32px;
      display: flex; align-items: center; justify-content: center;
      border: 0; border-radius: 6px;
      background: transparent;
      color: #5C6370;
      cursor: pointer;
      transition: background-color 160ms ease, color 160ms ease;
    }
    .onb-icon-btn svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    @media (hover: hover) and (pointer: fine) {
      .onb-icon-btn:hover { background: #F2F4F7; color: #0E1116; }
    }
    .onb-widget-body { padding: 10px 18px 18px; }
    .onb-progress { display: flex; gap: 4px; margin-bottom: 14px; }
    .onb-dot { flex: 1; height: 4px; border-radius: 2px; background: #EEF0F2; }
    .onb-dot.done { background: #0E1116; }
    .onb-dot.active { background: #1E5FD8; }
    .onb-title { font-size: 17px; font-weight: 700; letter-spacing: -0.01em; line-height: 1.3; margin-bottom: 6px; }
    .onb-text { font-size: 14px; line-height: 1.55; color: #3A404A; margin-bottom: 16px; }
    .onb-text strong { color: #0E1116; font-weight: 600; }
    .onb-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .onb-btn {
      min-height: 40px;
      padding: 0 16px;
      border: 0;
      border-radius: 6px;
      font: inherit;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 160ms ease, color 160ms ease, transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
    }
    .onb-btn:active { transform: scale(0.97); }
    .onb-btn-skip { background: transparent; color: #5C6370; padding: 0 8px; }
    .onb-btn-next { background: #0E1116; color: #FFFFFF; }
    .onb-btn-next:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
    @media (hover: hover) and (pointer: fine) {
      .onb-btn-skip:hover { color: #0E1116; }
      .onb-btn-next:hover:not(:disabled) { background: #2A2F37; }
    }
    .onb-warning {
      display: none;
      margin-bottom: 12px;
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid #FDE68A;
      background: #FFFBEB;
      color: #92400E;
      font-size: 13px;
      line-height: 1.45;
    }
    .onb-warning.show { display: block; }
    .onb-mini {
      position: fixed;
      right: max(24px, env(safe-area-inset-right));
      bottom: max(24px, env(safe-area-inset-bottom));
      display: flex; align-items: center; gap: 8px;
      min-height: 44px;
      padding: 0 16px 0 8px;
      border: 0;
      border-radius: 999px;
      background: #0E1116;
      color: #FFFFFF;
      font-family: 'Sora', system-ui, sans-serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      z-index: 9999;
      box-shadow: 0 8px 24px rgba(14, 17, 22, 0.22);
      animation: onbIn 220ms cubic-bezier(0.23, 1, 0.32, 1);
      transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
    }
    .onb-mini:active { transform: scale(0.97); }
    .onb-mini-progress {
      width: 28px; height: 28px;
      display: flex; align-items: center; justify-content: center;
      border-radius: 50%;
      background: #FFC53D;
      color: #0E1116;
      font-size: 13px;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }
    .onb-done {
      position: fixed;
      left: 50%;
      bottom: max(24px, env(safe-area-inset-bottom));
      transform: translateX(-50%);
      display: flex; align-items: center; gap: 10px;
      max-width: calc(100vw - 32px);
      padding: 12px 18px;
      border-radius: 10px;
      background: #0E1116;
      color: #FFFFFF;
      font-family: 'Sora', system-ui, sans-serif;
      font-size: 14px;
      font-weight: 600;
      z-index: 9999;
      box-shadow: 0 8px 24px rgba(14, 17, 22, 0.22);
      animation: onbToast 260ms cubic-bezier(0.23, 1, 0.32, 1);
      transition: opacity 200ms ease;
    }
    .onb-done svg { width: 18px; height: 18px; fill: none; stroke: #2FCB7F; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; flex-shrink: 0; }
    @keyframes onbToast { from { opacity: 0; transform: translate(-50%, 8px); } }
    @media (max-width: 560px) {
      .onb-widget {
        left: 12px; right: 12px;
        bottom: max(12px, env(safe-area-inset-bottom));
        width: auto; max-width: none;
        transform-origin: bottom center;
      }
      .onb-mini { right: 12px; bottom: max(12px, env(safe-area-inset-bottom)); }
    }
    @media (prefers-reduced-motion: reduce) {
      .onb-spotlight, .onb-widget, .onb-mini, .onb-done { animation: none; }
    }
  `;
  document.head.appendChild(style);
}

let onbRepositionner = null;

function retirerWidget() {
  document.querySelectorAll('#onb-widget, .onb-mini, .onb-spotlight').forEach(el => el.remove());
  if (onbRepositionner) {
    window.removeEventListener('resize', onbRepositionner);
    onbRepositionner = null;
  }
}

function afficherWidget(step, target) {
  retirerWidget();

  if (target) {
    const padding = 6;
    const spot = document.createElement('div');
    spot.className = 'onb-spotlight';
    spot.setAttribute('aria-hidden', 'true');
    const placer = () => {
      const r = target.getBoundingClientRect();
      spot.style.cssText = `top:${r.top + window.scrollY - padding}px; left:${r.left + window.scrollX - padding}px; width:${r.width + padding * 2}px; height:${r.height + padding * 2}px;`;
    };
    placer();
    document.body.appendChild(spot);
    onbRepositionner = placer;
    window.addEventListener('resize', onbRepositionner);

    const rect = target.getBoundingClientRect();
    if (rect.top < 80 || rect.top > window.innerHeight - 220) {
      const reduit = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: Math.max(0, rect.top + window.scrollY - 88), behavior: reduit ? 'auto' : 'smooth' });
      setTimeout(placer, 600);
    }
  }

  if (estReduit()) {
    afficherMini(step);
    return;
  }

  const totalSteps = ONBOARDING_STEPS.length;
  let progressHTML = '<div class="onb-progress" aria-hidden="true">';
  for (let i = 1; i <= totalSteps; i++) {
    const cls = i < step.id ? 'done' : (i === step.id ? 'active' : '');
    progressHTML += `<div class="onb-dot ${cls}"></div>`;
  }
  progressHTML += '</div>';

  const widget = document.createElement('div');
  widget.id = 'onb-widget';
  widget.className = 'onb-widget';
  widget.setAttribute('role', 'dialog');
  widget.setAttribute('aria-modal', 'false');
  widget.setAttribute('aria-labelledby', 'onb-title');
  widget.innerHTML = `
    <div class="onb-widget-header">
      <div class="onb-widget-tag">Tutoriel · étape ${step.id} sur ${totalSteps}</div>
      <div class="onb-widget-actions">
        <button type="button" class="onb-icon-btn" onclick="basculerReduction()" title="Réduire" aria-label="Réduire le tutoriel">
          <svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <button type="button" class="onb-icon-btn" onclick="stopperOnboarding()" title="Fermer" aria-label="Fermer le tutoriel">
          <svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </div>
    <div class="onb-widget-body">
      ${progressHTML}
      <div class="onb-title" id="onb-title">${step.title}</div>
      <div class="onb-text">${step.text}</div>
      <div class="onb-warning" id="onb-warning" role="alert"></div>
      <div class="onb-actions">
        <button type="button" class="onb-btn onb-btn-skip" onclick="stopperOnboarding()">Passer le tutoriel</button>
        <button type="button" class="onb-btn onb-btn-next" id="onb-btn-next">${step.nextLabel || 'Suivant'}</button>
      </div>
    </div>
  `;

  document.body.appendChild(widget);
  document.getElementById('onb-btn-next').addEventListener('click', () => handleNextOnboarding(step));
}

function afficherMini(step) {
  const mini = document.createElement('button');
  mini.type = 'button';
  mini.className = 'onb-mini';
  mini.setAttribute('aria-label', `Rouvrir le tutoriel, étape ${step.id} sur ${ONBOARDING_STEPS.length}`);
  mini.onclick = basculerReduction;
  mini.innerHTML = `<span class="onb-mini-progress" aria-hidden="true">${step.id}</span>Tutoriel`;
  document.body.appendChild(mini);
}

function afficherFinOnboarding() {
  injecterStylesOnboarding();
  const toast = document.createElement('div');
  toast.className = 'onb-done';
  toast.setAttribute('role', 'status');
  toast.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>Tu connais SUM'IT. Bonne course !`;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; }, 3600);
  setTimeout(() => toast.remove(), 3900);
}

async function handleNextOnboarding(step) {
  const btn = document.getElementById('onb-btn-next');
  const warning = document.getElementById('onb-warning');

  if (step.checkCondition) {
    btn.disabled = true;
    btn.textContent = 'Vérification…';
    try {
      const ok = await step.checkCondition();
      if (!ok) {
        warning.textContent = step.conditionMessage || 'Action non terminée.';
        warning.classList.add('show');
        btn.disabled = false;
        btn.textContent = step.nextLabel || 'Suivant';
        return;
      }
    } catch (e) { /* on laisse passer */ }
  }

  switch (step.nextAction) {
    case 'goto:profil':
    case 'goto:simulateur':
    case 'goto:bilan': {
      const page = step.nextAction.split(':')[1];
      setOnboardingStep(step.id + 1);
      retirerWidget();
      if (getPageCourante() === page) afficherEtapeOnboarding(step.id + 1);
      else window.location.href = pathTo(page);
      break;
    }
    case 'finish':
      stopperOnboarding();
      afficherFinOnboarding();
      break;
    case 'next':
    default: {
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
}

function pathTo(page) {
  const path = window.location.pathname;
  const inPages = path.includes('/pages/');
  if (page === 'home') return inPages ? '../' : '/';
  if (inPages) return `${page}.html`;
  return `/pages/${page}.html`;
}
