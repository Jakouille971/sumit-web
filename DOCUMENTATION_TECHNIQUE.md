# SUM'IT — Documentation technique

> Trail running & randonnée — Prédicteur de temps de course personnalisé
> Version 2 — Bêta (refonte de l'interface, octobre 2026)

---

## 1. Vue d'ensemble

SUM'IT est une application web qui prédit les temps de course trail/rando d'un coureur sur une trace GPX cible, en se basant sur son **propre historique GPX** plutôt que sur des moyennes génériques.

### 1.1 Stack technique

```
Frontend  : HTML / CSS / JavaScript vanilla (sans framework, sans build)
Backend   : Python 3.13 + FastAPI + Uvicorn
Calcul    : NumPy + Pandas + GPXpy
Base      : PostgreSQL (Neon) en production, SQLite en local
Comptes   : Google OAuth (jeton JWT), Strava OAuth (import d'activités)
Frontend déployé sur : Vercel
Backend déployé sur  : Render (free tier)
Cartes    : Leaflet 1.9 + fond CARTO clair (données OpenStreetMap)
PDF       : jsPDF + html2canvas (côté navigateur)
Mails     : EmailJS (avis, questionnaire, notifications roadmap)
Police    : Sora, auto-hébergée (fonts/, licence OFL), aucun appel à Google Fonts
```

### 1.2 Architecture

```
┌──────────────┐         ┌─────────────────┐
│   Frontend   │  HTTPS  │  Backend Python │
│   (Vercel)   │ ──────► │    (Render)     │
│              │         │   FastAPI       │
│  HTML/CSS/JS │ ◄────── │   /api/...      │
└──────────────┘  JSON   └─────────────────┘
        │                          │
        ▼                          ▼
  localStorage (jeton)       PostgreSQL (Neon)
  sessionStorage (profil)    comptes, activités,
                             simulations épinglées
```

---

## 2. Algorithme de calcul

### 2.1 Pipeline complet

```
GPX brut
   │
   ├─► 1. Parsing GPX (gpxpy)
   ├─► 2. Calcul des distances (Haversine)
   ├─► 3. Lissage altimétrique (rolling 30pts)
   ├─► 4. Détection et exclusion des arrêts
   ├─► 5. Calcul de pente par segment
   ├─► 6. Classification terrain (7 types)
   ├─► 7. Application coefficient Minetti
   ├─► 8. Calcul VEP brute → VEP plafonnée
   ├─► 9. Lissage VEP (rolling 15pts)
   ├─► 10. Analyse FC par zones
   └─► 11. Agrégation multi-traces

Résultat : Profil coureur complet
```

### 2.2 VEP — Vitesse Équivalente Plat

C'est le cœur du système. Concept emprunté à l'étude de **Alberto Minetti (2002)** sur le coût énergétique de la marche/course en pente.

**Principe :** convertir une vitesse réelle sur pente en vitesse équivalente sur du plat, pour comparer des efforts physiologiquement équivalents.

```python
VEP = vitesse_réelle × coefficient_Minetti(pente)
```

**Table Minetti utilisée :**

| Pente (%) | Coefficient |
|-----------|-------------|
| -25       | 1.28        |
| -20       | 1.17        |
| -15       | 1.08        |
| -10       | 1.03        |
| -5        | 0.95        |
| 0         | 1.00        |
| +5        | 1.22        |
| +10       | 1.58        |
| +15       | 2.14        |
| +20       | 2.90        |
| +25       | 3.94        |

Interpolation linéaire entre les paliers, plafonnée à ±25%.

### 2.3 Classification des 7 terrains

```python
def classifier_terrain(pente_pct):
    if pente >= 15:    return 'montee_raide'      # ≥ +15%
    elif pente >= 8:   return 'montee_soutenue'   # +8 à +15%
    elif pente >= 3:   return 'montee_douce'      # +3 à +8%
    elif pente >= -3:  return 'plat'              # -3 à +3%
    elif pente >= -8:  return 'descente_douce'    # -3 à -8%
    elif pente >= -15: return 'descente_soutenue' # -8 à -15%
    else:              return 'descente_raide'    # ≤ -15%
```

### 2.4 Plafonnement VEP par terrain

Évite les valeurs aberrantes dues au bruit GPS :

| Terrain          | VEP_MAX (km/h) |
|------------------|----------------|
| Montée raide     | 12.0           |
| Montée soutenue  | 13.0           |
| Montée douce     | 14.0           |
| Plat             | 20.0           |
| Descente douce   | 16.0           |
| Descente soutenue| 14.0           |
| Descente raide   | 12.0           |

### 2.5 Pondération multi-traces (TRIPLE)

Quand plusieurs GPX sont importés, agrégation par **triple pondération** :

```
poids_total = poids_distance × poids_temporel × poids_type_sortie
```

**Poids distance :** distance de chaque segment de terrain (plus tu cours sur un terrain, plus c'est représentatif).

**Poids temporel :** décroissance exponentielle, demi-vie 180 jours.
```python
poids_temp = max(0.10, exp(-ln(2) × jours / 180))
```
→ Une course d'il y a 6 mois compte 50% d'une course récente.

**Poids type de sortie :**
- Course officielle : 1.00
- Entraînement     : 0.70
- Sortie tranquille: 0.40

### 2.6 Coefficient Course/Entraînement via FC

**Innovation clé** — la plupart des coureurs n'importent que des entraînements, où ils s'économisent (~75% FCmax). En course, ils poussent à ~87% FCmax. Sans coefficient correctif, les prédictions sur-estiment massivement les temps de course.

**Formule :**
```python
coefficient = FC_cible_course / FC_moyenne_entraînement

# Exemple : entraînements à 75% FCmax, course visée à 87%
# → coefficient = 0.87 / 0.75 = 1.16 → +16% de VEP en course
```

**Calibration intelligente :**
- Si l'utilisateur a importé des **vraies courses** → utilise leur FC moyenne réelle
- Sinon → utilise une cible par défaut de 0.87 (87% FCmax)

**Plafonnement :** entre ×1.05 et ×1.30 (sécurité contre les profils aberrants).

### 2.7 Catégories de distance

Une même VEP normalisée s'exprime différemment selon la longueur de la course (gestion endurance) :

```python
CATEGORIES = [
  {'nom': 'Court',  'min':  0, 'max':  25, 'facteur': 1.15},
  {'nom': 'Moyen',  'min': 25, 'max':  50, 'facteur': 1.00},
  {'nom': 'Long',   'min': 50, 'max':  80, 'facteur': 0.88},
  {'nom': 'Ultra',  'min': 80, 'max': 999, 'facteur': 0.78},
]
```

Sur un trail court tu vas plus vite qu'un ultra, normalisation pour comparer entre courses de longueurs différentes.

---

## 3. Modèle de fatigue (simulation)

Pendant la simulation, deux coefficients de fatigue s'appliquent à chaque segment :

### 3.1 Fatigue mécanique

Basée sur le **dénivelé positif cumulé**. Activation à 50% du D+ total :

```python
ratio_dplus = D+_cumulé / D+_total

if ratio_dplus <= 0.50:
    coef_meca = 1.0
else:
    coef_meca = 1.0 - 0.15 × ((ratio_dplus - 0.50) / 0.50)
```

→ Maximum -15% de vitesse en fin de course très vallonnée.

### 3.2 Batterie énergétique

Drain par seconde dépendant de la zone FC :

```python
ZONES_FC = {
    1: drain 0.02 %/h (récupération, < 65% FCmax)
    2: drain 0.05 %/h (endurance,    65-75%)
    3: drain 0.10 %/h (tempo,        75-85%)
    4: drain 0.18 %/h (seuil,        85-92%)
    5: drain 0.30 %/h (max,          92-100%)
}

# Activation seuil à 50% batterie
if batterie >= 50%:
    coef_batt = 1.0
else:
    coef_batt = 1.0 - 0.25 × ((0.50 - batt/100) / 0.50)
```

→ Maximum -25% de vitesse quand la batterie tombe à 0%.

### 3.3 Vitesse réelle finale

```python
VEP_référence = VEP_norm × facteur_catégorie × coefficient_course
VEP_réelle    = VEP_référence × coef_meca × coef_batt
vitesse_ms    = (VEP_réelle / 3.6) / coefficient_Minetti
```

---

## 4. Archétypes de coureur

Détermination automatique du profil dominant à partir des scores de terrain.

### 4.1 Calcul des scores

```python
score_terrain = min(100, (VEP_normalisée / VEP_référence_terrain) × 50)
```

Référence VEP par terrain (basée sur trail-runner moyen) :
| Terrain          | REF_VEP (km/h) |
|------------------|----------------|
| Montée raide     | 6.5            |
| Montée soutenue  | 7.0            |
| Montée douce     | 7.5            |
| Plat             | 9.0            |
| Descente douce   | 8.5            |
| Descente soutenue| 7.5            |
| Descente raide   | 6.5            |

### 4.2 Logique de classification

```
SI score_montée >= 65 ET score_montée > score_descente + 15
    → LE GRIMPEUR

SINON SI score_descente >= 65 ET score_descente > score_montée + 15
    → LE DESCENDEUR

SINON SI score_plat >= 65 ET score_plat > montée ET score_plat > descente
    → L'EXPLOSIF

SINON SI score_régularité >= 70 ET écart_max-min < 20
    → L'ÉQUILIBRÉ

SINON
    → LE TENACE
```

### 4.3 Fourchettes dynamiques

Calculées à partir du **coefficient de variation (CV)** des VEP par terrain :

```python
cv = std(VEP_par_tranche) / mean(VEP_par_tranche)
fourchette_basse = max(0.05, cv × 0.8)   # entre 5% et 30%
fourchette_haute = min(0.30, cv × 1.2)
```

→ Plus tu es régulier sur un terrain, plus la fourchette est serrée.

---

## 5. Simulation point par point

### 5.1 Algorithme

Pour chaque segment GPS du parcours cible :

```python
1. Récupérer terrain, pente, distance
2. Récupérer VEP_norm de l'utilisateur pour ce terrain
3. Appliquer facteur catégorie + coefficient course
4. Calculer fatigue mécanique (D+ cumulé)
5. Calculer fatigue batterie
6. VEP_réelle = VEP_ref × coef_meca × coef_batt
7. vitesse_ms = (VEP_réelle / 3.6) / coef_minetti
8. duree_segment = distance_m / vitesse_ms
9. Décrémenter batterie
10. Cumuler temps total
```

### 5.2 Sorties générées

- **Temps total estimé** + format `HhMMmSSs`
- **Fourchettes** basse (top condition) et haute (jour difficile)
- **Allure moyenne** en min/km
- **Batterie finale** (0-100%)
- **Temps de passage** à chaque ravitaillement avec fourchettes
- **Répartition par terrain** (% du temps total)
- **Profil altimétrique** échantillonné à 150 points pour le graphique

---

## 6. Frontend — Visualisations

### 6.1 Graphique altimétrique coloré

SVG dessiné à la largeur réelle de l'écran, **une seule teinte bleue** dont l'intensité suit l'allure prédite (lissage sur 5 points) :

| Allure       | Teinte      |
|--------------|-------------|
| < 10'/km     | `#9DBEF2`   |
| 10-13'/km    | `#5C8FE6`   |
| 13-18'/km    | `#1E5FD8`   |
| > 18'/km     | `#0E3A8C`   |

Courbe d'allure en surimpression, FC estimée en pointillés, repères de ravitos avec kilomètre, infobulle au survol et au toucher.

### 6.2 Carte Leaflet

Tracé GPS sur fond CARTO clair (données OpenStreetMap), marqueurs départ et arrivée.

### 6.3 PDF côté navigateur

Génération entièrement côté client via **jsPDF + html2canvas** :
- Aucun fichier ne transite par le serveur
- Roadbook A4 blanc : temps, allure, profil de coureur utilisé, profil de course, scores de pente, répartition par terrain, tableau des passages (heures comprises si une heure de départ est saisie)
- Le profil de coureur imprimé est celui qui a calculé la simulation (enregistré avec la simulation épinglée)

### 6.4 Interface (refonte V2)

- **Accueil** : construit autour des photos de Jess Meniere. Le titre « Prédis / ta course » reste en place pendant qu'une bande de photos défile entre ses deux moitiés ; quatre verbes plein écran (Importe, Simule, Cours, Compare) ; les huit archétypes en cartes sur une photo tenue ; l'horaire de la CCC réglable (heure de départ, pause aux ravitos) ; questions fréquentes, grand bouton « Simule », contact. Palette tirée des photos : vert bouteille `#133621`, or `#F4D96C`, blanc de brouillard `#EEF0EA`.
- **Photos** : `assets/photos/`, en WebP (600, 960, 1440 px, 2 400 px pour la photo paysage), chargées à la demande. Crédit « Photos : Jess Meniere » dans le pied de toutes les pages.
- **Écrans de l'application** (profil, simulateur, bilan, compte, à venir) : système sobre, une police (Sora), encre `#0E1116`, bleu de données `#1E5FD8`, vert et rouge réservés aux écarts.
- **Pages réservées** : un visiteur non connecté voit ce que la page lui apportera, avec un aperçu construit sur les vraies données de la démo CCC.
- **Accessibilité et mobile** : navigation au clavier, focus visibles, champs à 16 px (pas de zoom iOS), zones sûres des écrans à encoche, mouvement réduit respecté.
- **Tutoriel** en 7 étapes, non bloquant, qui suit le visiteur de page en page.

---

## 7. Endpoints API

### 7.1 `GET /`

Health check.
```json
{ "status": "ok", "app": "SUM'IT API", "version": "1.0.0" }
```

### 7.2 `POST /api/analyser-profil`

**Entrée (multipart/form-data) :**
- `fichiers` : liste de fichiers GPX
- `types` : JSON ["course", "entrainement", "sortie"]
- `fcmax` : entier (bpm)
- `profil_type` : "trail" ou "rando"

**Sortie :**
```json
{
  "status": "ok",
  "nb_traces": 4,
  "traces": [...],
  "profil": {
    "montee_raide": { "vep_norm": 7.4, "score": 82, ... },
    ...
  },
  "drain_moy_h": 0.074,
  "coefficient_course": {
    "coefficient": 1.17,
    "gain_pct": 17.0,
    "fc_moy_entrainement": 0.75,
    "fc_course_utilisee": 0.87,
    ...
  },
  "archetype": {
    "key": "grimpeur",
    "nom": "Le Grimpeur",
    "desc": "...",
    "forces": [...],
    "faiblesses": [...],
    "conseil": "..."
  }
}
```

### 7.3 `POST /api/simuler`

**Entrée (multipart/form-data) :**
- `fichier_cible` : GPX de la course visée
- `ravitos_km` : "12, 25, 42"
- `profil_json` : JSON du profil (récupéré depuis sessionStorage)
- `drain_moy_h`, `coefficient`, `fcmax` : flottants

**Sortie :**
```json
{
  "distance_km": 57.4,
  "dplus_m": 3272,
  "categorie": { "nom": "Long", "emoji": "🟠", "facteur": 0.88 },
  "temps_fmt": "14h44m12s",
  "bas_fmt": "13h07m55s",
  "haut_fmt": "17h10m08s",
  "allure_moy": 15.4,
  "batt_finale": 0.0,
  "ravitos": [
    { "km": 12, "temps_fmt": "2h39m18s", "batterie_pct": 80, ... },
    ...
  ],
  "repartition": {
    "montee_raide": { "pct": 34.2, "temps_fmt": "5h02m..." },
    ...
  },
  "profil_chart": [
    { "dist_km": 0, "altitude": 535, "terrain": "plat", "vitesse_kmh": 9.2 },
    ...
  ]
}
```

---

## 8. Limites connues / pistes d'amélioration

### 8.1 Limites actuelles

- **Pas de prise en compte météo** (chaleur, pluie, vent)
- **Pas d'altitude réelle** (efforts en altitude > 2000m)
- **Modèle uniforme** entre coureurs jeunes/seniors
- **Pas de gestion nutrition** (apports, ravitaillements)
- **Free tier Render** : serveur s'endort après 15 min, 30-60s au réveil

### 8.2 Feuille de route (identique à la page « À venir »)

- **V1 Fondations — en ligne** : analyse GPX multi-traces, huit archétypes, simulateur (ravitos, fourchette, heures de passage), import Strava, roadbook PDF, simulations épinglées, terrain OpenStreetMap, compte Google, tutoriel.
- **V2 Analyse — en ligne** : bilan réel contre prédit avec recalibrage, évolution du profil, bilans épinglés.
- **V3 Partage et jour J — à venir** : lien public de simulation, comparaison de plusieurs simulations, mode jour J sur mobile, application iOS et Android.
- **V4 Coaching — plus tard** : plan nutrition entre ravitos, séances types selon l'archétype, plan d'entraînement vers la course objectif.
- Pistes de modèle : coefficient météo (chaleur, vent), coefficient altitude au-delà de 2 000 m.

---

## 9. Confidentialité

- **Compte** : connexion Google ; la base stocke l'adresse e-mail, le prénom, la FC max et les profils calculés.
- **Activités** : les données utiles au recalcul du profil (résumé et trace compactée) sont stockées et liées au compte ; chaque activité peut être supprimée par l'utilisateur, ce qui recalcule son profil.
- **Simulations épinglées** : la trace GPX de la course est conservée avec la simulation pour pouvoir la rouvrir et la recalculer ; suppression possible depuis « Mon compte ».
- **Strava** : lecture seule des activités, déconnexion possible à tout moment ; les activités déjà importées sont conservées.
- **Aucun pistage** : pas de Google Analytics, pas de cookies tiers, police auto-hébergée.
- **Tiers appelés par le navigateur** : CARTO (fonds de carte), unpkg, cdnjs et jsDelivr (bibliothèques), EmailJS (uniquement à l'envoi d'un message ou d'un questionnaire).
- **Suppression du compte** : sur demande par le formulaire de contact (pas encore en libre-service).

---

## 10. Sources scientifiques

- **Minetti A.E., et al.** (2002) — *Energy cost of walking and running at extreme uphill and downhill slopes*. Journal of Applied Physiology.
- **Karvonen, M.J.** (1957) — *The effects of training on heart rate*. Annales Medicinae Experimentalis et Biologiae Fenniae. (Pour les zones FC.)
- **Costill, D.L., et al.** — Études sur le coût énergétique en course longue distance.

---

## 11. Repository et stack

```
sumit-web/
├── api.py                  # Backend FastAPI (analyse, simulation, comptes, activités, simulations)
├── auth.py                 # Google OAuth + JWT
├── strava.py               # Strava OAuth + import
├── db.py                   # Modèles SQLAlchemy (User, Profile, Activity)
├── coefficient_course.py   # Coefficient course / entraînement
├── requirements.txt        # Dépendances Python
├── index.html              # Accueil
├── favicon.svg             # Icône
├── og-image.png            # Image d'aperçu des liens (1200 × 630)
├── fonts/                  # Sora (woff2, latin et latin étendu) + licence OFL
├── assets/
│   ├── photos/             # Photos de Jess Meniere (WebP, plusieurs tailles)
│   ├── ccc-utmb.gpx        # Trace de la démo CCC
│   └── profil-demo.json    # Profil de coureur d'exemple (Grimpeur, 12 sorties)
├── css/
│   └── style.css           # Système de design commun
├── js/
│   ├── main.js             # Navigation
│   ├── api-client.js       # Client API, jeton, profil en session, réveil du serveur
│   ├── nav-user.js         # Barre de navigation (compte, tutoriel, menu mobile)
│   ├── onboarding.js       # Tutoriel en 7 étapes
│   └── pictos.js           # Pictogrammes des archétypes
└── pages/
    ├── profil.html         # Import GPX/Strava, profil, évolution, activités
    ├── simulateur.html     # Simulation, carte, roadbook PDF, épinglage
    ├── bilan.html          # Réel contre prédit, recalibrage
    ├── compte.html         # Réglages, Strava, simulations épinglées
    └── avenir.html         # Feuille de route
```

**Lignes de code (approx.) :**
- Backend Python : ~3 800 lignes
- Frontend (HTML, CSS, JS) : ~9 500 lignes

---

*Documentation technique de SUM'IT — V2 bêta*
*Auteur : Jake Plumey · 2026*
