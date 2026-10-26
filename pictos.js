// ══════════════════════════════════════════════════════════════
//  SUM'IT — pictos.js
//  Les huit archétypes dessinés comme des signatures de pente :
//  chaque trait est le profil de terrain où le coureur excelle.
//  Utilisé par la page d'accueil et par la page profil.
// ══════════════════════════════════════════════════════════════

(function () {
  const trait = (d, extra = '') =>
    `<svg viewBox="0 0 44 44" aria-hidden="true" focusable="false"><path d="M4 39H40" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.35"/><path d="${d}" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>${extra}</svg>`;

  const PICTOS = {
    'Cabri':      trait('M5 35H12L18 12L23 24L28 6L33 35H39', '<circle cx="28" cy="6" r="2.4" fill="currentColor"/>'),
    'Grimpeur':   trait('M5 35L31 9L39 17', '<circle cx="31" cy="9" r="2.4" fill="currentColor"/>'),
    'Funambule':  trait('M5 7L11 13L9 17L17 21L15 26L25 29L23 33L39 35', '<circle cx="5" cy="7" r="2.4" fill="currentColor"/>'),
    'Descendeur': trait('M5 7C18 9 22 33 39 35', '<path d="M7 24H14M10 30H17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'),
    'Équilibré':  trait('M5 35L22 11L39 35', '<circle cx="22" cy="11" r="2.4" fill="currentColor"/>'),
    'Diesel':     trait('M5 31Q11 27 17 31T29 29T39 17', '<circle cx="39" cy="17" r="2.4" fill="currentColor"/>'),
    'Rouleur':    trait('M5 27Q10 23 15 27T25 27T35 27Q37 25.5 39 27'),
    'Tenace':     trait('M4 34L9 23L13 30L18 19L22 28L27 16L31 26L36 14L40 22'),
    'Combattant': trait('M5 33L13 21L19 27L27 13L33 21L39 15'),
  };

  function cle(nom) {
    return String(nom || '').replace(/^L'/i, '').replace(/^Le\s+/i, '').replace(/^La\s+/i, '').trim();
  }

  window.SUMIT_PICTOS = PICTOS;
  window.pictoArchetype = function (nom) {
    return PICTOS[cle(nom)] || PICTOS['Combattant'];
  };
})();
