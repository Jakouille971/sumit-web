// ══════════════════════════════════════════════════════════════
//  SUM'IT — catalogue des courses : données, formats et dessins
//  Utilisé par pages/catalogue.html, pages/evenement.html et le simulateur.
//  Les données viennent de assets/catalogue/catalogue.json, produit par
//  outils/integrer_catalogue.py (voir outils/catalogue/LISEZMOI.md).
// ══════════════════════════════════════════════════════════════
(function () {
  const BASE = (location.pathname.includes('/pages/') ? '../' : '') + 'assets/catalogue/';
  const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  const MOIS_COURT = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
  const JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
  const ESP = ' ';   // espace fine insécable (milliers, unités)

  let promesse = null;
  function charger() {
    if (!promesse) {
      promesse = fetch(BASE + 'catalogue.json', { cache: 'no-cache' })
        .then(r => { if (!r.ok) throw new Error('Le catalogue n\'a pas pu être chargé.'); return r.json(); })
        .catch(e => { promesse = null; throw e; });
    }
    return promesse;
  }

  // ── Dates ─────────────────────────────────────────────────────
  const pad = n => String(n).padStart(2, '0');
  function aujourdhui() {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }
  function decoupe(iso) { const [a, m, j] = iso.split('-').map(Number); return { a, m, j }; }
  function finDeMois(iso) {       // '2027-01' -> '2027-01-31'
    const { a, m } = decoupe(iso);
    return `${a}-${pad(m)}-${pad(new Date(a, m, 0).getDate())}`;
  }
  function fin(ev) {
    const d = ev.date_fin || ev.date_debut;
    return d.length === 7 ? finDeMois(d) : d;
  }
  function moisPrecis(ev) { return ev.date_debut.length === 7; }
  // Mois de rangement : celui du début de l'événement
  function cleMois(ev) { return ev.date_debut.slice(0, 7); }
  function libelleMois(cle) {
    const { a, m } = decoupe(cle + '-01');
    return `${MOIS[m - 1].charAt(0).toUpperCase()}${MOIS[m - 1].slice(1)} ${a}`;
  }

  function dates(ev, court) {
    const M = court ? MOIS_COURT : MOIS;
    if (moisPrecis(ev)) {
      const { a, m } = decoupe(ev.date_debut + '-01');
      return `${court ? M[m - 1] : MOIS[m - 1]} ${a}`;
    }
    const d = decoupe(ev.date_debut);
    const f = ev.date_fin && ev.date_fin !== ev.date_debut ? decoupe(ev.date_fin) : null;
    const j1 = d.j === 1 ? '1er' : d.j;
    if (!f) return `${j1} ${M[d.m - 1]} ${d.a}`;
    if (f.m === d.m && f.a === d.a) return `${j1}–${f.j} ${M[d.m - 1]} ${d.a}`;
    if (f.a === d.a) return `${j1} ${M[d.m - 1]} – ${f.j} ${M[f.m - 1]} ${d.a}`;
    return `${j1} ${M[d.m - 1]} ${d.a} – ${f.j} ${M[f.m - 1]} ${f.a}`;
  }
  function jour(iso, court) {
    const { a, m, j } = decoupe(iso);
    const w = new Date(a, m - 1, j).getDay();
    return court ? `${JOURS[w].slice(0, 3)}. ${j} ${MOIS_COURT[m - 1]}` : `${JOURS[w]} ${j === 1 ? '1er' : j} ${MOIS[m - 1]}`;
  }
  function heure(hhmm) {
    const [h, mn] = hhmm.split(':');
    return `${+h}${ESP}h${ESP}${mn}`;
  }
  // Jours restants avant le début (0 = aujourd'hui), négatif si commencé
  function joursAvant(ev) {
    if (moisPrecis(ev)) return null;
    const { a, m, j } = decoupe(ev.date_debut);
    const t = decoupe(aujourdhui());
    return Math.round((new Date(a, m - 1, j) - new Date(t.a, t.m - 1, t.j)) / 86400000);
  }

  // ── Nombres ───────────────────────────────────────────────────
  function km(x) {
    const r = Math.round(x * 10) / 10;
    return (Number.isInteger(r) ? String(r) : r.toFixed(1).replace('.', ',')).replace(/\B(?=(\d{3})+(?!\d))/g, ESP);
  }
  function entier(x) { return String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ESP); }
  function dplus(c) {
    if (c.dplus_m != null) return { valeur: c.dplus_m, trace: false };
    if (c.trace) return { valeur: c.trace.dplus_m, trace: true };
    return null;
  }
  function distancesTexte(ev) {
    return ev.courses.map(c => km(c.distance_km)).join(' · ') + `${ESP}km`;
  }
  function nbTraces(ev) { return ev.courses.filter(c => c.gpx).length; }

  // ── Sélection ─────────────────────────────────────────────────
  function aVenir(cat) {
    const t = aujourdhui();
    return (cat.evenements || []).filter(ev => fin(ev) >= t);
  }
  function trouver(cat, evId, courseId) {
    const ev = (cat.evenements || []).find(e => e.id === evId);
    if (!ev) return {};
    return { ev, course: courseId ? ev.courses.find(c => c.id === courseId) : null };
  }
  function url(nom) { return BASE + nom; }
  function photoSrcset(ev) {
    if (!ev.photo) return null;
    const tailles = Object.keys(ev.photo).map(Number).sort((a, b) => a - b);
    return {
      src: url(ev.photo['960'] || ev.photo[String(tailles[tailles.length - 1])]),
      srcset: tailles.map(w => `${url(ev.photo[String(w)])} ${w}w`).join(', '),
    };
  }

  // ── Dessins ───────────────────────────────────────────────────
  // Teintes par saison, prises dans la palette du site (heures de course)
  function teintes(ev) {
    const m = +ev.date_debut.slice(5, 7);
    const v = Math.floor(graine(ev.id + '·teinte')() * 3);
    const hiver = [
      { fond: '#1B4A66', loin: '#2B6A8C', pres: '#8DB5CC', crete: '#FFFFFF' },
      { fond: '#133621', loin: '#1B4A66', pres: '#8DB5CC', crete: '#FFFFFF' },
      { fond: '#2B6A8C', loin: '#1B4A66', pres: '#E1EDF3', crete: '#FFFFFF' }];
    const printemps = [
      { fond: '#24533A', loin: '#3E6630', pres: '#9FBF7A', crete: '#F4D96C' },
      { fond: '#3E6630', loin: '#24533A', pres: '#C9BC78', crete: '#FFFFFF' },
      { fond: '#2B6A8C', loin: '#3E6630', pres: '#9FBF7A', crete: '#F4D96C' }];
    const automne = [
      { fond: '#133621', loin: '#24533A', pres: '#C9BC78', crete: '#F4D96C' },
      { fond: '#24533A', loin: '#133621', pres: '#F4D96C', crete: '#FFFFFF' },
      { fond: '#1B4A66', loin: '#133621', pres: '#C9BC78', crete: '#F4D96C' }];
    // Teintes de la palette du site, selon la saison ; trois variantes par saison
    if (m === 12 || m <= 2) return hiver[v];
    if (m <= 8) return printemps[v];
    return automne[v];
  }
  function graine(txt) {
    let h = 2166136261;
    for (let i = 0; i < txt.length; i++) { h ^= txt.charCodeAt(i); h = Math.imul(h, 16777619); }
    return () => { h ^= h << 13; h ^= h >>> 17; h ^= h << 5; return ((h >>> 0) % 10000) / 10000; };
  }
  function crete(alea, n, base, ampl, W, H) {
    const pts = [];
    let y = base;
    for (let i = 0; i <= n; i++) {
      y += (alea() - 0.5) * ampl;
      y = Math.max(H * 0.18, Math.min(H * 0.9, y));
      pts.push([W * i / n, y]);
    }
    return pts;
  }
  const chemin = (pts, W, H) => `M0 ${H} ` + pts.map(([x, y]) => `L${x.toFixed(1)} ${y.toFixed(1)}`).join(' ') + ` L${W} ${H} Z`;

  // Visuel d'un événement sans photo : son vrai profil si une trace existe,
  // sinon une ligne de crêtes propre à l'événement (décor, pas un profil).
  function visuel(ev, opts) {
    opts = opts || {};
    const W = 300, H = 200, alea = graine(ev.id);
    let t = teintes(ev);
    // Dans le bandeau vert d'une fiche, le fond doit se détacher du bandeau
    if (opts.surVert && t.fond === '#133621') t = Object.assign({}, t, { fond: '#24533A', loin: '#1A4429' });
    const loin = crete(alea, 9, H * 0.48, H * 0.22, W, H);
    let devant;
    const longue = ev.courses.find(c => c.trace && c.trace.profil && c.trace.profil.length > 4);
    if (longue) {
      const p = longue.trace.profil, kmMax = p[p.length - 1][0] || 1;
      const amin = Math.min(...p.map(x => x[1])), amax = Math.max(...p.map(x => x[1]));
      const ech = v => H * 0.92 - (v - amin) / Math.max(1, amax - amin) * H * 0.5;
      devant = p.map(([k, a]) => [k / kmMax * W, ech(a)]);
    } else {
      devant = crete(alea, 14, H * 0.66, H * 0.2, W, H);
    }
    const ligne = devant.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
    const titre = longue ? `Profil du ${km(longue.distance_km)} km` : '';
    return `<svg class="cat-visuel" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" ${titre ? `role="img" aria-label="${titre}"` : 'aria-hidden="true"'}>
      <rect width="${W}" height="${H}" fill="${t.fond}"/>
      <path d="${chemin(loin, W, H)}" fill="${t.loin}"/>
      <path d="${chemin(devant, W, H)}" fill="${t.pres}" opacity="0.55"/>
      <path d="${ligne}" fill="none" stroke="${t.crete}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
    </svg>`;
  }

  // Profil d'altitude d'une course (fiche événement)
  function profilSVG(c) {
    const p = c.trace && c.trace.profil;
    if (!p || p.length < 3) return '';
    const W = 640, H = 150, g = 34, b = 22, h = 8;
    const kmMax = p[p.length - 1][0] || 1;
    const amin = c.trace.alt_min, amax = Math.max(c.trace.alt_max, amin + 50);
    const x = k => g + (k / kmMax) * (W - g - 6);
    const y = a => h + (1 - (a - amin) / (amax - amin)) * (H - h - b);
    const ligne = p.map(([k, a], i) => `${i ? 'L' : 'M'}${x(k).toFixed(1)} ${y(a).toFixed(1)}`).join(' ');
    const aire = `${ligne} L${x(kmMax).toFixed(1)} ${H - b} L${g} ${H - b} Z`;
    const pas = kmMax > 120 ? 40 : kmMax > 60 ? 20 : kmMax > 25 ? 10 : 5;
    let graduations = '';
    for (let k = pas; k < kmMax - pas * 0.4; k += pas) {
      graduations += `<text x="${x(k).toFixed(1)}" y="${H - 6}" text-anchor="middle">${k}</text>`;
    }
    const ravitos = (c.ravitos || []).map(r =>
      `<line x1="${x(r.km).toFixed(1)}" x2="${x(r.km).toFixed(1)}" y1="${H - b}" y2="${H - b - 6}" class="cat-pf-ravito"><title>${esc(r.nom || 'Ravito')} · km ${km(r.km)}</title></line>`).join('');
    return `<svg class="cat-profil" viewBox="0 0 ${W} ${H}" role="img" aria-label="Profil d'altitude : ${km(c.trace.distance_km)} km, de ${entier(amin)} à ${entier(c.trace.alt_max)} m d'altitude">
      <line x1="${g}" x2="${W - 6}" y1="${H - b}" y2="${H - b}" class="cat-pf-base"/>
      <path d="${aire}" class="cat-pf-aire"/>
      <path d="${ligne}" class="cat-pf-ligne"/>
      ${ravitos}
      <text x="${g - 6}" y="${y(amax) + 4}" text-anchor="end">${entier(amax)}</text>
      <text x="${g - 6}" y="${y(amin) + 4}" text-anchor="end">${entier(amin)}</text>
      <text x="${g}" y="${H - 6}" text-anchor="start">0</text>
      ${graduations}
      <text x="${W - 6}" y="${H - 6}" text-anchor="end">${km(kmMax)} km</text>
    </svg>`;
  }

  // Typographie française des textes saisis : milliers, %, unités insécables
  function typo(t) {
    return String(t || '')
      .replace(/(\d) (\d{3})(?!\d)/g, `$1${ESP}$2`)
      .replace(/(\d) (%|km|m\b|h\b)/g, '$1\u00a0$2')
      .replace(/« /g, '«\u00a0').replace(/ »/g, '\u00a0»')
      .replace(/ ([:;!?])/g, '\u00a0$1');
  }

  function esc(t) {
    return String(t == null ? '' : t).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }

  const INSCRIPTIONS = { ouvertes: 'Inscriptions ouvertes', bientot: 'Inscriptions bientôt', complet: 'Complet', closes: 'Inscriptions closes' };

  window.sumitCatalogue = {
    charger, aujourdhui, fin, moisPrecis, cleMois, libelleMois, dates, jour, heure, joursAvant,
    km, entier, dplus, distancesTexte, nbTraces, aVenir, trouver, url, photoSrcset,
    visuel, profilSVG, esc, typo, INSCRIPTIONS,
  };
})();
