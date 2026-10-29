# SUM'IT — Plan your peaks

Prédicteur de temps de course pour le trail et la randonnée. SUM'IT apprend l'allure du coureur sur ses propres traces GPX (montée, plat, descente), en tire un profil, et prédit son temps et son heure de passage à chaque ravito d'une course cible.

- Démo sans compte : `pages/simulateur.html?demo=ccc` (la CCC, 98,4 km, 5 742 m D+)
- Documentation complète : `DOCUMENTATION_TECHNIQUE.md`

## Architecture

- **Frontend** : HTML, CSS et JavaScript sans framework ni étape de build (Vercel)
- **Backend** : Python FastAPI (Render), PostgreSQL (Neon)
- **Comptes** : Google OAuth ; import Strava

## Lancement local

### Backend
```bash
pip install -r requirements.txt
python api.py
```
API disponible sur http://localhost:8000 (SQLite par défaut si `DATABASE_URL` n'est pas défini).

### Frontend
```bash
python -m http.server 3000
```
Site disponible sur http://localhost:3000

## Déploiement

### Variables d'environnement (Render)

- `DATABASE_URL` : base Postgres (Neon)
- `JWT_SECRET` : secret des sessions (obligatoire en production)
- `ADMIN_KEY` : clé d'accès à la page `pages/stats.html` (chiffres d'usage) ; une longue chaîne aléatoire
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `FRONTEND_URL`

Les nouvelles tables (`mesures`, `terrain_cache`) sont créées automatiquement au démarrage du serveur.

### Démo CCC précalculée

`assets/demo-ccc.json` contient le résultat de la démo. Après toute modification du modèle (`api.py`) ou de `assets/profil-demo.json` :

```bash
python outils/generer_demo.py
```

### Catalogue des courses

`pages/catalogue.html` et `pages/evenement.html` lisent `assets/catalogue/catalogue.json`. Mise à jour mensuelle, manuelle et vérifiée : voir `outils/catalogue/LISEZMOI.md`. Intégration d'un lot (contrôle des GPX, images, sitemap, rapport) :

```bash
python3 outils/integrer_catalogue.py --lot outils/catalogue/lots/AAAA-MM.json
```

### Fichiers

Pousser l'ensemble des fichiers, y compris `fonts/`, `assets/Photos/`, `assets/demo-ccc.json`, `js/pictos.js`, `favicon.svg`, `og-image.png`, `robots.txt` et `sitemap.xml`.

Photos : Jess Meniere. Le crédit figure dans le pied de chaque page.

Les fichiers CSS et JS sont versionnés par `?v=20261030` : changer ce numéro à chaque mise en production force le rechargement chez les visiteurs.
