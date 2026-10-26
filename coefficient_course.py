# ══════════════════════════════════════════════════════════════
#  SUM'IT — Coefficient Course/Entraînement via Fréquence Cardiaque
#  À intégrer dans sumit.py — remplace/complète les fonctions concernées
# ══════════════════════════════════════════════════════════════

"""
PRINCIPE :
En entraînement, tu cours à ~70-75% de FCmax → ta VEP mesurée est "sous-estimée"
En course, tu pousses à ~85-92% de FCmax → tu vas nettement plus vite à même effort perçu

Le coefficient est calculé depuis tes PROPRES données FC :
  coeff_course = FC_cible_course / FC_moyenne_entrainement

Exemple (Jake) :
  FC moyenne entraînements : 75% FCmax
  FC cible en course       : 88% FCmax
  Coefficient              : 0.88 / 0.75 = 1.173 → +17.3% de VEP

Ce coefficient est appliqué à la VEP normalisée lors de la simulation.
"""

import numpy as np

FCMAX = 193  # À adapter selon le coureur

# ── Zones FC et leur niveau d'effort relatif ──────────────────
ZONES_FC_EFFORT = {
    1: {'min': 0.00, 'max': 0.65, 'label': 'Récupération',   'effort_relatif': 0.55},
    2: {'min': 0.65, 'max': 0.75, 'label': 'Endurance',       'effort_relatif': 0.70},
    3: {'min': 0.75, 'max': 0.85, 'label': 'Tempo',           'effort_relatif': 0.80},
    4: {'min': 0.85, 'max': 0.92, 'label': 'Seuil',           'effort_relatif': 0.88},
    5: {'min': 0.92, 'max': 1.00, 'label': 'Max',             'effort_relatif': 0.96},
}

def calculer_fc_ratio_moyen(df, type_sortie):
    """
    Calcule le ratio FC/FCmax moyen d'une trace
    en excluant les arrêts et les valeurs aberrantes.
    """
    if df['fc_bpm'].isna().all():
        # Pas de FC → on utilise des valeurs par défaut selon le type
        defaults = {'course': 0.87, 'entrainement': 0.75, 'sortie': 0.65}
        return defaults.get(type_sortie, 0.75)

    fc_valide = df['fc_bpm'].dropna()
    # Suppression des valeurs aberrantes (< 100 ou > FCmax)
    fc_valide = fc_valide[(fc_valide > 100) & (fc_valide <= FCMAX * 1.05)]

    if len(fc_valide) < 10:
        defaults = {'course': 0.87, 'entrainement': 0.75, 'sortie': 0.65}
        return defaults.get(type_sortie, 0.75)

    return fc_valide.median() / FCMAX


def calculer_coefficient_course(resultats, fc_cible_course=0.87):
    """
    Calcule le coefficient de performance course vs entraînement.

    Paramètres :
    - resultats       : liste des traces analysées (avec type_sortie et df)
    - fc_cible_course : ratio FC/FCmax visé en course (défaut 87%)

    Retourne :
    - coefficient     : multiplicateur à appliquer sur la VEP en simulation de course
    - details         : dict avec toutes les infos pour transparence

    Exemple :
      Si tes entraînements sont à 74% FCmax en moyenne,
      et qu'en course tu cibles 87% FCmax :
      coefficient = 0.87 / 0.74 = 1.176 → +17.6% de VEP en course
    """

    # ── FC moyenne des entraînements ──────────────────────────
    fc_entrainements = []
    poids_e = []

    fc_courses = []
    poids_c = []

    for r in resultats:
        df = r['df']
        type_s = r['type_sortie']
        fc_ratio = calculer_fc_ratio_moyen(df, type_s)
        dist = r['dist_km']

        if type_s == 'entrainement':
            fc_entrainements.append(fc_ratio)
            poids_e.append(dist)
        elif type_s == 'course':
            fc_courses.append(fc_ratio)
            poids_c.append(dist)
        # Les 'sortie' tranquilles ne sont pas prises en compte

    # ── Calcul du ratio FC entraînement ───────────────────────
    if fc_entrainements:
        fc_moy_entrainement = np.average(fc_entrainements, weights=poids_e)
    else:
        fc_moy_entrainement = 0.75  # Valeur par défaut si aucun entraînement

    # ── Ratio FC réel des courses (si disponible) ─────────────
    if fc_courses:
        fc_moy_course_reelle = np.average(fc_courses, weights=poids_c)
        # On utilise la FC réelle des courses si on en a
        fc_course_utilisee = fc_moy_course_reelle
        source = "FC réelle des courses importées"
    else:
        # Pas de course → on utilise la cible par défaut
        fc_course_utilisee = fc_cible_course
        source = f"FC cible par défaut ({fc_cible_course:.0%} FCmax)"

    # ── Coefficient final ──────────────────────────────────────
    if fc_moy_entrainement > 0:
        coefficient = fc_course_utilisee / fc_moy_entrainement
    else:
        coefficient = 1.10  # Fallback sécurisé

    # Plafonnement raisonnable : entre +5% et +30%
    coefficient = max(1.05, min(1.30, coefficient))

    details = {
        'fc_moy_entrainement':    fc_moy_entrainement,
        'fc_course_utilisee':     fc_course_utilisee,
        'source_fc_course':       source,
        'coefficient':            coefficient,
        'gain_pct':               (coefficient - 1) * 100,
        'nb_entrainements':       len(fc_entrainements),
        'nb_courses_reelles':     len(fc_courses),
    }

    return coefficient, details


def afficher_coefficient_course(details):
    """Affiche le détail du coefficient course calculé."""
    print("\n" + "="*65)
    print("     🏆 COEFFICIENT COURSE / ENTRAÎNEMENT")
    print("="*65)
    print(f"\n  FC moyenne entraînements : {details['fc_moy_entrainement']:.1%} FCmax")
    print(f"  FC course utilisée       : {details['fc_course_utilisee']:.1%} FCmax")
    print(f"  Source                   : {details['source_fc_course']}")
    print(f"\n  Coefficient appliqué     : ×{details['coefficient']:.3f}")
    print(f"  Gain de performance      : +{details['gain_pct']:.1f}%")

    if details['nb_courses_reelles'] > 0:
        print(f"\n  ✅ Calibré sur {details['nb_courses_reelles']} course(s) réelle(s)")
        print("     → Coefficient très fiable, basé sur tes vraies performances")
    else:
        print(f"\n  ⚠️  Aucune course importée — coefficient estimé")
        print("     → Importe des traces de courses pour affiner ce coefficient")
        print("     → Pour l'instant : VEP entraînement × facteur FC standard")

    if details['gain_pct'] < 8:
        print("\n  💡 Ton gain est faible : tu t'entraînes déjà à haute intensité")
    elif details['gain_pct'] > 22:
        print("\n  💡 Ton gain est élevé : tu ménages bien tes entraînements")
    else:
        print("\n  💡 Gain typique pour un trail runner bien entraîné")


# ══════════════════════════════════════════════════════════════
#  INTÉGRATION DANS simuler_course()
#  Remplace dans sumit.py la fonction simuler_course() :
# ══════════════════════════════════════════════════════════════

def simuler_course_v2(df_cible, profil, drain_moy_h, cat_cible, coefficient_course=1.0):
    """
    Version améliorée avec coefficient course intégré.
    La VEP de référence est multipliée par coefficient_course
    pour refléter la performance réelle en compétition vs entraînement.
    """
    import pandas as pd

    # Constantes
    MINETTI_TABLE = {
        -25:1.28,-20:1.17,-15:1.08,-10:1.03,
        -5:0.95,0:1.00,5:1.22,10:1.58,
        15:2.14,20:2.90,25:3.94
    }

    def coef_minetti(p):
        pc = max(-25, min(25, p))
        ks = sorted(MINETTI_TABLE.keys())
        for i in range(len(ks)-1):
            p1,p2 = ks[i],ks[i+1]
            if p1 <= pc <= p2:
                t = (pc-p1)/(p2-p1)
                return MINETTI_TABLE[p1]+t*(MINETTI_TABLE[p2]-MINETTI_TABLE[p1])
        return 1.0

    def coefs_fatigue(dep_cum, dep_tot, dplus_cum, dplus_tot, batt):
        ratio_d = dplus_cum/dplus_tot if dplus_tot > 0 else 0
        coef_m  = 1.0 if ratio_d <= 0.50 else 1.0 - 0.15*((ratio_d-0.50)/0.50)
        br      = batt/100
        coef_b  = 1.0 if br >= 0.50 else 1.0 - 0.25*((0.50-br)/0.50)
        return coef_m, coef_b

    dep_totale   = df_cible['dist_eq_plat_m'].sum()
    dplus_totale = df_cible['dplus_cumule_m'].max()
    batterie_pct = 100.0
    drain_par_s  = drain_moy_h / 3600
    dep_cum      = 0.0
    temps_s      = 0.0
    resultats    = []

    for _, row in df_cible.iterrows():
        if row['dist_m'] == 0:
            continue

        dep_cum   += row['dist_eq_plat_m']
        terrain    = row['terrain']

        # VEP normalisée × facteur catégorie × COEFFICIENT COURSE
        vep_norm   = profil.get(terrain, {}).get('vep_norm', 7.0)
        vep_ref    = vep_norm * cat_cible['facteur'] * coefficient_course

        coef_m, coef_b = coefs_fatigue(
            dep_cum, dep_totale,
            row['dplus_cumule_m'], dplus_totale,
            batterie_pct
        )
        coef_total = coef_m * coef_b
        vep_reelle = vep_ref * coef_total

        vitesse_ms = (vep_reelle / 3.6) / row['coef_minetti']
        vitesse_ms = max(vitesse_ms, 0.3)
        duree_s    = row['dist_m'] / vitesse_ms

        batterie_pct = max(0, batterie_pct - drain_par_s * duree_s * 100)
        temps_s     += duree_s

        resultats.append({
            'dist_km':         row['dist_cumulee_km'],
            'altitude':        row['altitude'],
            'terrain':         terrain,
            'effort_pct':      dep_cum / dep_totale * 100,
            'coef_meca':       coef_m,
            'coef_batt':       coef_b,
            'coef_total':      coef_total,
            'coef_course':     coefficient_course,
            'batterie_pct':    batterie_pct,
            'vep_reelle':      vep_reelle,
            'vitesse_kmh':     vitesse_ms * 3.6,
            'temps_s':         temps_s,
            'duree_segment_s': duree_s,
        })

    return pd.DataFrame(resultats).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
#  MODIFICATION DU MAIN dans sumit.py
#  Ajoute ces lignes APRÈS agreger_profil() et AVANT simuler_course()
# ══════════════════════════════════════════════════════════════
"""
# Dans le MAIN de sumit.py, remplace :
#   df_sim = simuler_course(df_cible, profil, drain_agrege, cat_cible)
# Par :

coefficient_course, details_coeff = calculer_coefficient_course(
    resultats,
    fc_cible_course=0.87  # 87% FCmax = intensité course typique trail
)
afficher_coefficient_course(details_coeff)

df_sim = simuler_course_v2(
    df_cible, profil, drain_agrege, cat_cible,
    coefficient_course=coefficient_course
)
"""
