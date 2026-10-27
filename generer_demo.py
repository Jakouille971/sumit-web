"""
Régénère assets/demo-ccc.json : le résultat précalculé de la démo CCC du simulateur.
À relancer après toute modification du modèle (api.py) ou du profil de démo.

    python outils/generer_demo.py        (depuis la racine du dépôt)

Le calcul passe par l'API elle-même (en local, sans serveur) : la démo affiche
exactement ce que le simulateur calculerait.
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.chdir(RACINE)

import numpy as np
from fastapi.testclient import TestClient
import api

GPX = os.path.join(RACINE, 'assets', 'ccc-utmb.gpx')
SORTIE = os.path.join(RACINE, 'assets', 'demo-ccc.json')
RAVITOS = [(14.1, 'Refuge Bertone'), (25.8, 'Arnouvaz'), (39.8, 'La Fouly'),
           (55.4, 'Champex-Lac'), (69.6, 'Trient'), (80.1, 'Vallorcine')]

profil = json.load(open(os.path.join(RACINE, 'assets', 'profil-demo.json'), encoding='utf-8'))
client = TestClient(api.app)
r = client.post('/api/simuler',
                files={'fichier_cible': ('CCC-UTMB.gpx', open(GPX, 'rb'), 'application/gpx+xml')},
                data={'ravitos_km': ','.join(str(k) for k, _ in RAVITOS),
                      'ravitos_noms': json.dumps({f'{k:.1f}': n for k, n in RAVITOS}),
                      'profil_json': json.dumps(profil['profil']),
                      'drain_moy_h': str(profil['drain_moy_h']), 'coefficient': str(profil['coefficient']),
                      'fcmax': str(profil['fcmax'])})
r.raise_for_status()
res = r.json()
res['heure_depart'] = '09:00'
res['profil_resume'] = {
    'archetype': {'nom': profil['archetype']['nom']}, 'vep_globale': profil['vep_globale'],
    'coefficient': profil['coefficient'], 'drain_moy_h': profil['drain_moy_h'],
    'fcmax': profil['fcmax'], 'nb_traces': profil['nb_traces'],
}

df, _, _ = api.charger_gpx(open(GPX, 'rb').read())
dist, lat, lon = df['dist_cum'].values, df['lat'].values, df['lon'].values
pas = max(1, len(df) // 600)
carte = [[round(float(a), 5), round(float(b), 5)] for a, b in zip(lat[::pas], lon[::pas])]
carte.append([round(float(lat[-1]), 5), round(float(lon[-1]), 5)])
points = []
for p in res['profil_chart']:
    i = min(max(int(np.searchsorted(dist, p['dist_km'])), 0), len(dist) - 1)
    points.append([round(float(lat[i]), 5), round(float(lon[i]), 5)])

demo = {
    'version': 1,
    'nom_course': 'CCC — UTMB (démo)',
    'fichier': {'nom': 'CCC 2025 — UTMB', 'distance': '98,4 km', 'dplus': '5 742 m', 'categorie': 'Ultra'},
    'ravitos': [[k, n] for k, n in RAVITOS],
    'profil': {k: profil[k] for k in ('profil', 'drain_moy_h', 'coefficient', 'archetype', 'fcmax',
                                      'prenom', 'nb_traces', 'vep_globale', 'profil_type')},
    'resultat': res,
    'carte': carte,
    'points_graphique': points,
}
with open(SORTIE, 'w', encoding='utf-8') as f:
    json.dump(demo, f, ensure_ascii=False, separators=(',', ':'))
print(f"demo-ccc.json : {os.path.getsize(SORTIE)} octets, temps prédit {res['temps_fmt']}")
