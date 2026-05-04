# SUM'IT — Plan your peaks

Trail running & randonnée — Analyse GPX, profil coureur et simulateur de course.

## Architecture

- **Frontend** : HTML/CSS/JS (servi par Vercel)
- **Backend** : Python FastAPI (servi par Render)

## Lancement local

### Backend
```bash
pip install -r requirements.txt
python api.py
```
API disponible sur http://localhost:8000

### Frontend
```bash
python -m http.server 3000
```
Site disponible sur http://localhost:3000
