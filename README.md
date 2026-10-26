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

Pousser l'ensemble des fichiers, y compris `fonts/`, `js/pictos.js`, `favicon.svg` et `og-image.png`. Les fichiers CSS et JS sont versionnés par `?v=20261026` : changer ce numéro à chaque mise en production force le rechargement chez les visiteurs.
