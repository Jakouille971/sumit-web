#!/usr/bin/env python3
"""
SUM'IT — intégration d'un lot du catalogue des courses
=======================================================

Ce script prépare, sans rien mettre en ligne, tout ce qu'il faut téléverser sur
GitHub pour publier un lot de courses :

  1. il applique le lot proposé (ajouts, modifications, retraits d'événements)
     au catalogue publié, assets/catalogue/catalogue.json ;
  2. il contrôle chaque fichier déposé dans le dossier d'intégration :
       <evenement>__<course>.gpx   la trace d'une course
       <evenement>__photo.jpg      la photo de l'événement (jpg, png ou webp)
       <evenement>__logo.png       le logo (png, jpg, webp ou svg)
     - GPX : lisible, assez de points, altitudes présentes ; distance et D+
       recalculés comme sur le serveur et comparés aux chiffres annoncés ;
       points de passage (<wpt>) lus comme ravitos ; profil d'altitude ;
     - images : redimensionnées et converties en WebP (si Pillow est installé) ;
  3. il retire les événements terminés depuis plus de 7 jours ;
  4. il met à jour sitemap.xml ;
  5. il écrit un rapport (outils/catalogue/rapports/) et rassemble les fichiers
     nouveaux ou modifiés dans outils/catalogue/a-televerser/, avec les mêmes
     dossiers que le dépôt : il suffit de glisser ce contenu sur GitHub.

Rien n'est écrit si une erreur bloquante est trouvée (sauf avec --forcer).

Utilisation, depuis la racine du dépôt :
  python3 outils/integrer_catalogue.py --lot outils/catalogue/lots/2026-12.json
  python3 outils/integrer_catalogue.py --lot ... --simuler      (contrôle seul)
  python3 outils/integrer_catalogue.py                         (fichiers seuls)

Python 3.8 ou plus, sans dépendance. Pillow (pip install Pillow) est conseillé
pour convertir les photos ; sans lui, elles sont copiées telles quelles.
"""

import argparse
import datetime as dt
import difflib
import json
import math
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image, ImageOps
except Exception:  # Pillow absent : les images seront copiées sans conversion
    Image = None

SITE = 'https://sumit-web-nine.vercel.app'
RE_ID = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
RE_DATE = re.compile(r'^\d{4}-\d{2}(-\d{2})?$')
RE_HEURE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
INSCRIPTIONS = {None, 'ouvertes', 'bientot', 'complet', 'closes'}

# Tolérances entre les chiffres annoncés par l'organisation et la trace
ECART_DIST_ALERTE, ECART_DIST_ERREUR = 0.05, 0.20
ECART_DPLUS_ALERTE, ECART_DPLUS_ERREUR = 0.12, 0.30
POINTS_PROFIL = 80
RETRAIT_APRES_JOURS = 7

CHAMPS_EVENEMENT = ['id', 'statut', 'nom', 'commune', 'departement', 'region', 'date_debut', 'date_fin',
                    'date_confirmee', 'description', 'site_officiel', 'inscription_url', 'inscriptions',
                    'gpx_disponible_le', 'photo', 'photo_credit', 'logo', 'courses', 'sources', 'maj']
CHAMPS_COURSE = ['id', 'nom', 'distance_km', 'dplus_m', 'jour', 'heure_depart', 'depart', 'arrivee',
                 'ravitos', 'gpx', 'trace']


# ══════════════════════════════════════════════════════════════
#  Journal du contrôle
# ══════════════════════════════════════════════════════════════
class Journal:
    def __init__(self):
        self.erreurs, self.alertes, self.infos = [], [], []

    def erreur(self, ou, msg): self.erreurs.append((ou, msg))
    def alerte(self, ou, msg): self.alertes.append((ou, msg))
    def info(self, ou, msg): self.infos.append((ou, msg))


def suggestion(mot, choix):
    m = difflib.get_close_matches(mot, list(choix), n=1, cutoff=0.5)
    return f' (vouliez-vous dire « {m[0]} » ?)' if m else ''


def fr_nombre(x, dec=0):
    s = f'{x:,.{dec}f}'.replace(',', ' ').replace('.', ',')
    return s


# ══════════════════════════════════════════════════════════════
#  Dates
# ══════════════════════════════════════════════════════════════
def fin_de_periode(date_txt):
    """'2027-01' -> dernier jour de janvier ; '2027-01-10' -> ce jour."""
    if not date_txt:
        return None
    if len(date_txt) == 7:
        a, m = map(int, date_txt.split('-'))
        suivant = dt.date(a + (m == 12), m % 12 + 1, 1)
        return suivant - dt.timedelta(days=1)
    return dt.date.fromisoformat(date_txt)


def debut_de_periode(date_txt):
    if not date_txt:
        return None
    return dt.date.fromisoformat(date_txt + ('-01' if len(date_txt) == 7 else ''))


# ══════════════════════════════════════════════════════════════
#  GPX : lecture et calculs (mêmes règles que le serveur, api.py)
# ══════════════════════════════════════════════════════════════
def _local(tag):
    return tag.rsplit('}', 1)[-1].lower()


def lire_gpx(chemin):
    racine = ET.parse(chemin).getroot()
    trk, rte, wpts = [], [], []
    for el in racine.iter():
        nom = _local(el.tag)
        if nom not in ('trkpt', 'rtept', 'wpt'):
            continue
        try:
            lat, lon = float(el.get('lat')), float(el.get('lon'))
        except (TypeError, ValueError):
            continue
        ele = None
        textes = {}
        for enfant in el:
            n = _local(enfant.tag)
            if n == 'ele':
                try:
                    ele = float((enfant.text or '').strip())
                except ValueError:
                    ele = None
            elif n in ('name', 'desc', 'cmt', 'type', 'sym'):
                textes[n] = (enfant.text or '').strip()
        if nom == 'trkpt':
            trk.append((lat, lon, ele))
        elif nom == 'rtept':
            rte.append((lat, lon, ele))
        else:
            wpts.append({'lat': lat, 'lon': lon, 'ele': ele, **textes})
    return (trk or rte), ('trace' if trk else 'route'), wpts


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def mediane(vals):
    v = sorted(vals)
    n = len(v)
    if not n:
        return 0.0
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def calculer_trace(points):
    """Distance, D+, D-, altitudes, cumul ; reprend charger_gpx() de api.py."""
    n = len(points)
    d = [0.0] * n
    for i in range(1, n):
        d[i] = haversine(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])
    positives = [x for x in d if x > 0]
    med = mediane(positives) if positives else 0
    sauts = 0
    for i in range(1, n):
        if d[i] > 200.0 and med > 0:      # saut GPS aberrant : remplacé par la médiane
            d[i] = med
            sauts += 1
    cumul = [0.0] * n
    for i in range(1, n):
        cumul[i] = cumul[i - 1] + d[i]

    brutes = [p[2] if p[2] is not None else 0.0 for p in points]
    # médiane glissante centrée sur 3 points (rolling(3, center=True, min_periods=1))
    alt = []
    for i in range(n):
        fen = brutes[max(0, i - 1):min(n, i + 2)]
        alt.append(mediane(fen))

    # D+/D- par hystérésis de 2 m, à l'identique du serveur
    seuil = 2.0
    dplus = dmoins = 0.0
    if n > 1:
        ref, sens = alt[0], 0
        for i in range(1, n):
            delta = alt[i] - ref
            if sens >= 0 and delta >= seuil:
                dplus += delta; ref = alt[i]; sens = 1
            elif sens <= 0 and delta <= -seuil:
                dmoins += -delta; ref = alt[i]; sens = -1
            elif (sens > 0 and delta < 0) or (sens < 0 and delta > 0):
                ref = alt[i - 1]
                delta2 = alt[i] - ref
                if delta2 >= seuil:
                    dplus += delta2; ref = alt[i]; sens = 1
                elif delta2 <= -seuil:
                    dmoins += -delta2; ref = alt[i]; sens = -1
                else:
                    sens = 0
    return {
        'cumul': cumul, 'alt': alt, 'sauts': sauts,
        'distance_km': cumul[-1] / 1000 if n else 0.0,
        'dplus_m': dplus, 'dmoins_m': dmoins,
        'alt_min': min(alt) if alt else 0, 'alt_max': max(alt) if alt else 0,
    }


def profil(cumul, alt, n=POINTS_PROFIL):
    total = cumul[-1]
    if total <= 0:
        return []
    res, j = [], 0
    for k in range(n + 1):
        cible = total * k / n
        while j < len(cumul) - 1 and cumul[j] < cible:
            j += 1
        res.append([round(cumul[j] / 1000, 2), int(round(alt[j]))])
    return res


def ravitos_depuis_wpts(points, cumul, wpts):
    """Même règle que le simulateur (lireGPXCourse) : à moins de 300 m de la
    trace, hors départ et arrivée, un point par tranche de 300 m."""
    if not points or not wpts:
        return []
    total_km = cumul[-1] / 1000
    cos_lat = math.cos(math.radians(points[len(points) // 2][0]))
    res = []
    for w in wpts:
        best, best_d = -1, float('inf')
        for i, p in enumerate(points):
            dy = (p[0] - w['lat']) * 111320
            dx = (p[1] - w['lon']) * 111320 * cos_lat
            d2 = dx * dx + dy * dy
            if d2 < best_d:
                best, best_d = i, d2
        if math.sqrt(best_d) > 300:
            continue
        km = round(cumul[best] / 100) / 10
        if km < 0.5 or km > total_km - 0.5:
            continue
        nom = re.sub(r'\s+', ' ', w.get('name') or w.get('desc') or w.get('cmt') or '').strip()[:60]
        res.append({'km': km, 'nom': nom})
    res.sort(key=lambda r: r['km'])
    uniques = []
    for r in res:
        if uniques and r['km'] - uniques[-1]['km'] < 0.3:
            continue
        uniques.append(r)
    return uniques[:30]


def ecrire_gpx(chemin, titre, points, alt_brutes, ravitos, cumul):
    """GPX propre : une seule trace (trk), altitudes, ravitos en <wpt>, sans horodatage."""
    def esc(t):
        return (str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))
    lignes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<gpx version="1.1" creator="SUM\'IT catalogue" xmlns="http://www.topografix.com/GPX/1/1">',
              f'  <metadata><name>{esc(titre)}</name></metadata>']
    for r in ravitos:
        # place chaque ravito sur la trace, au kilomètre indiqué
        cible = r['km'] * 1000
        i = min(range(len(cumul)), key=lambda k: abs(cumul[k] - cible))
        lat, lon = points[i][0], points[i][1]
        lignes.append(f'  <wpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{alt_brutes[i]:.1f}</ele>'
                      f'<name>{esc(r["nom"] or "Ravito")}</name><type>Ravitaillement</type></wpt>')
    lignes.append(f'  <trk><name>{esc(titre)}</name><trkseg>')
    for (lat, lon, _), a in zip(points, alt_brutes):
        lignes.append(f'    <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{a:.1f}</ele></trkpt>')
    lignes.append('  </trkseg></trk>')
    lignes.append('</gpx>')
    chemin.write_text('\n'.join(lignes) + '\n', encoding='utf-8')


# ══════════════════════════════════════════════════════════════
#  Images
# ══════════════════════════════════════════════════════════════
def traiter_photo(src, dossier, ev_id, j):
    ou = f'{ev_id} · photo'
    sorties = {}
    if Image is None:
        dest = dossier / f'{ev_id}__photo{src.suffix.lower()}'
        shutil.copyfile(src, dest)
        taille = dest.stat().st_size / 1e6
        j.alerte(ou, f'Pillow absent : photo copiée sans conversion ({taille:.1f} Mo). '
                     'Installer Pillow pour la convertir en WebP.')
        return {'960': dest.name, '600': dest.name}, [dest]
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        if im.width < 900:
            j.alerte(ou, f'photo petite ({im.width} px de large) : elle sera floue sur grand écran.')
        ratio = im.width / im.height
        if ratio < 1.1:
            j.alerte(ou, 'photo en hauteur ou carrée : les cases sont en 3:2, le cadrage coupera le haut et le bas.')
        fichiers = []
        for w in (1440, 960, 600):
            if w > im.width and w != 600:
                continue
            copie = im.copy()
            if copie.width > w:
                copie = copie.resize((w, round(w / ratio)), Image.LANCZOS)
            dest = dossier / f'{ev_id}__photo-{w}.webp'
            copie.save(dest, 'WEBP', quality=78, method=6)
            sorties[str(w)] = dest.name
            fichiers.append(dest)
        if '960' not in sorties:
            sorties['960'] = sorties.get('1440') or sorties['600']
        return sorties, fichiers


def traiter_logo(src, dossier, ev_id, j):
    ou = f'{ev_id} · logo'
    ext = src.suffix.lower()
    if ext == '.svg':
        txt = src.read_text(encoding='utf-8', errors='replace')
        if re.search(r'<script|on\w+\s*=|javascript:', txt, re.I):
            j.erreur(ou, 'le SVG contient du script : demander un PNG à l\'organisation ou nettoyer le fichier.')
            return None, []
        dest = dossier / f'{ev_id}__logo.svg'
        dest.write_text(txt, encoding='utf-8')
        return dest.name, [dest]
    if Image is None:
        dest = dossier / f'{ev_id}__logo{ext}'
        shutil.copyfile(src, dest)
        j.alerte(ou, 'Pillow absent : logo copié sans redimensionnement.')
        return dest.name, [dest]
    with Image.open(src) as im:
        im = im.convert('RGBA')
        if im.getbbox():
            im = im.crop(im.getbbox())   # retire les marges transparentes
        im.thumbnail((360, 180), Image.LANCZOS)
        dest = dossier / f'{ev_id}__logo.webp'
        im.save(dest, 'WEBP', quality=90, method=6)
        return dest.name, [dest]


# ══════════════════════════════════════════════════════════════
#  Lot : ajouts, modifications, retraits
# ══════════════════════════════════════════════════════════════
def appliquer_lot(catalogue, lot, j):
    par_id = {e['id']: e for e in catalogue['evenements']}
    retires, a_verifier = [], {}
    for prop in lot.get('evenements', []):
        ev_id = prop.get('id', '')
        action = prop.get('action', 'ajouter')
        if not RE_ID.match(ev_id or ''):
            j.erreur(ev_id or '?', 'identifiant invalide (minuscules, chiffres et tirets seulement).')
            continue
        if prop.get('a_verifier'):
            a_verifier[ev_id] = prop['a_verifier']
        if action == 'retirer':
            if ev_id in par_id:
                retires.append(par_id.pop(ev_id))
            else:
                j.alerte(ev_id, 'retrait demandé mais événement absent du catalogue.')
            continue
        if action == 'ajouter' and ev_id in par_id:
            j.info(ev_id, 'déjà au catalogue : la proposition est traitée comme une modification.')
            action = 'modifier'
        if action == 'modifier' and ev_id not in par_id:
            j.alerte(ev_id, 'modification d\'un événement absent du catalogue : il est ajouté.')
            action = 'ajouter'
        if action == 'ajouter':
            ev = {k: v for k, v in prop.items() if k not in ('action', 'a_verifier')}
            ev['courses'] = [{k: v for k, v in c.items() if k != 'action'} for c in prop.get('courses', [])
                             if c.get('action') != 'retirer']
            par_id[ev_id] = ev
        elif action == 'modifier':
            ev = par_id[ev_id]
            for k, v in prop.items():
                if k in ('action', 'a_verifier', 'courses', 'id'):
                    continue
                ev[k] = v
            if 'courses' in prop:
                courses = {c['id']: c for c in ev.get('courses', [])}
                ordre = [c['id'] for c in ev.get('courses', [])]
                for c in prop['courses']:
                    cid = c.get('id')
                    if c.get('action') == 'retirer':
                        courses.pop(cid, None)
                        continue
                    if cid in courses:
                        courses[cid].update({k: v for k, v in c.items() if k != 'action'})
                    else:
                        courses[cid] = {k: v for k, v in c.items() if k != 'action'}
                        ordre.append(cid)
                ev['courses'] = [courses[i] for i in ordre if i in courses]
        else:
            j.erreur(ev_id, f'action inconnue « {action} » (ajouter, modifier ou retirer).')
    catalogue['evenements'] = list(par_id.values())
    return retires, a_verifier


def valider(ev, j):
    ou = ev.get('id', '?')
    for champ in ('nom', 'commune', 'date_debut', 'description'):
        if not ev.get(champ):
            j.erreur(ou, f'champ « {champ} » manquant.')
    for champ in ('date_debut', 'date_fin', 'gpx_disponible_le'):
        v = ev.get(champ)
        if v and not RE_DATE.match(v):
            j.erreur(ou, f'{champ} « {v} » : format attendu AAAA-MM-JJ (ou AAAA-MM si le jour est inconnu).')
    if ev.get('date_debut') and ev.get('date_fin') and RE_DATE.match(ev['date_debut']) and RE_DATE.match(ev['date_fin']):
        if fin_de_periode(ev['date_fin']) < debut_de_periode(ev['date_debut']):
            j.erreur(ou, 'date_fin antérieure à date_debut.')
    if ev.get('inscriptions') not in INSCRIPTIONS:
        j.erreur(ou, f'inscriptions « {ev.get("inscriptions")} » : ouvertes, bientot, complet, closes ou null.')
    for champ in ('site_officiel', 'inscription_url'):
        v = ev.get(champ)
        if v and not v.startswith('https://') and not v.startswith('http://'):
            j.erreur(ou, f'{champ} doit être une adresse complète (https://…).')
    if len(ev.get('description') or '') > 600:
        j.alerte(ou, 'description longue (plus de 600 caractères) : la case l\'affiche en entier sur la fiche.')
    courses = ev.get('courses') or []
    if not courses:
        j.erreur(ou, 'aucune course.')
    vus = set()
    for c in courses:
        oc = f'{ou} · {c.get("id", "?")}'
        if not RE_ID.match(c.get('id') or ''):
            j.erreur(oc, 'identifiant de course invalide.')
        if c.get('id') in vus:
            j.erreur(oc, 'identifiant de course en double.')
        vus.add(c.get('id'))
        if not c.get('nom'):
            j.erreur(oc, 'nom de course manquant.')
        if not isinstance(c.get('distance_km'), (int, float)) or c['distance_km'] <= 0:
            j.erreur(oc, 'distance_km manquante ou invalide.')
        if c.get('dplus_m') is not None and (not isinstance(c['dplus_m'], (int, float)) or c['dplus_m'] < 0):
            j.erreur(oc, 'dplus_m invalide.')
        if c.get('heure_depart') and not RE_HEURE.match(c['heure_depart']):
            j.erreur(oc, f'heure_depart « {c["heure_depart"]} » : format HH:MM.')
        if c.get('jour') and not re.match(r'^\d{4}-\d{2}-\d{2}$', c['jour']):
            j.erreur(oc, 'jour : format AAAA-MM-JJ.')
        if c.get('jour') and ev.get('date_debut') and RE_DATE.match(ev['date_debut']):
            jour = dt.date.fromisoformat(c['jour'])
            deb = debut_de_periode(ev['date_debut'])
            fin = fin_de_periode(ev.get('date_fin') or ev['date_debut'])
            if not (deb <= jour <= fin):
                j.alerte(oc, f'jour {c["jour"]} hors des dates de l\'événement.')
        for r in c.get('ravitos') or []:
            if not isinstance(r.get('km'), (int, float)):
                j.erreur(oc, 'ravito sans km numérique.')


# ══════════════════════════════════════════════════════════════
#  Programme principal
# ══════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description='Intègre un lot au catalogue des courses SUM\'IT.')
    ap.add_argument('--lot', help='fichier de propositions du mois (JSON)')
    ap.add_argument('--depot', default=str(Path(__file__).resolve().parent.parent), help='racine du dépôt')
    ap.add_argument('--fichiers', help='dossier des GPX, photos et logos à intégrer')
    ap.add_argument('--paquet', help='dossier où rassembler les fichiers à téléverser')
    ap.add_argument('--aujourdhui', help='date du jour (AAAA-MM-JJ), pour les essais')
    ap.add_argument('--simuler', action='store_true', help='contrôle seul, rien n\'est écrit')
    ap.add_argument('--forcer', action='store_true', help='écrire malgré les erreurs')
    a = ap.parse_args()

    depot = Path(a.depot).resolve()
    dossier_cat = depot / 'assets' / 'catalogue'
    fichier_cat = dossier_cat / 'catalogue.json'
    entree = Path(a.fichiers).resolve() if a.fichiers else depot / 'outils' / 'catalogue' / 'a-integrer'
    paquet = Path(a.paquet).resolve() if a.paquet else depot / 'outils' / 'catalogue' / 'a-televerser'
    aujourdhui = dt.date.fromisoformat(a.aujourdhui) if a.aujourdhui else dt.date.today()
    j = Journal()

    # ── 1. Catalogue actuel + lot ───────────────────────────────
    if fichier_cat.exists():
        catalogue = json.loads(fichier_cat.read_text(encoding='utf-8'))
    else:
        catalogue = {'version': 1, 'maj': None, 'evenements': []}
        j.info('catalogue', 'aucun catalogue existant : création.')
    avant = json.dumps(catalogue, sort_keys=True, ensure_ascii=False)
    lot, retires, a_verifier = None, [], {}
    if a.lot:
        lot = json.loads(Path(a.lot).read_text(encoding='utf-8'))
        retires, a_verifier = appliquer_lot(catalogue, lot, j)

    # ── 2. Événements terminés ──────────────────────────────────
    gardes = []
    for ev in catalogue['evenements']:
        fin = fin_de_periode(ev.get('date_fin') or ev.get('date_debut'))
        if fin and fin < aujourdhui - dt.timedelta(days=RETRAIT_APRES_JOURS):
            retires.append(ev)
            j.info(ev['id'], f'terminé le {fin.isoformat()} : retiré du catalogue.')
        else:
            gardes.append(ev)
    catalogue['evenements'] = gardes
    for ev in catalogue['evenements']:
        valider(ev, j)
    par_id = {e['id']: e for e in catalogue['evenements']}

    # ── 3. Fichiers déposés ─────────────────────────────────────
    # les fichiers produits attendent dans un dossier temporaire : rien ne touche
    # au dépôt tant que le contrôle n'est pas passé
    sortie = Path(tempfile.mkdtemp(prefix='sumit-catalogue-'))
    produits, controles = [], {}
    depots = sorted(p for p in entree.iterdir() if p.is_file() and not p.name.startswith('.')) if entree.exists() else []
    for f in depots:
        m = re.match(r'^([a-z0-9-]+)__([a-z0-9-]+)\.([a-z0-9]+)$', f.name.lower())
        if not m:
            j.erreur(f.name, 'nom de fichier non reconnu : <evenement>__<course>.gpx, <evenement>__photo.jpg ou <evenement>__logo.png.')
            continue
        ev_id, role, ext = m.groups()
        if ev_id not in par_id:
            j.erreur(f.name, f'événement « {ev_id} » inconnu{suggestion(ev_id, par_id)}.')
            continue
        ev = par_id[ev_id]
        if role == 'photo':
            if ext not in ('jpg', 'jpeg', 'png', 'webp'):
                j.erreur(f.name, 'photo : jpg, png ou webp.')
                continue
            if not a.simuler:
                sorties, fs = traiter_photo(f, sortie, ev_id, j)
                ev['photo'] = sorties
                produits += fs
            if not ev.get('photo_credit'):
                j.alerte(f'{ev_id} · photo', 'crédit photo manquant (champ photo_credit) : l\'indiquer, ou l\'autorisation de l\'organisation.')
            continue
        if role == 'logo':
            if ext not in ('png', 'jpg', 'jpeg', 'webp', 'svg'):
                j.erreur(f.name, 'logo : png, jpg, webp ou svg.')
                continue
            if not a.simuler:
                nom, fs = traiter_logo(f, sortie, ev_id, j)
                if nom:
                    ev['logo'] = nom
                produits += fs
            continue
        if ext != 'gpx':
            j.erreur(f.name, 'seuls les .gpx sont acceptés pour les traces.')
            continue
        courses = {c['id']: c for c in ev.get('courses', [])}
        if role not in courses:
            j.erreur(f.name, f'course « {role} » inconnue pour {ev_id}{suggestion(role, courses)}.')
            continue
        c = courses[role]
        ou = f'{ev_id} · {role}'
        try:
            points, nature, wpts = lire_gpx(f)
        except ET.ParseError as e:
            j.erreur(ou, f'GPX illisible ({e}).')
            continue
        if len(points) < 50:
            j.erreur(ou, f'trace trop courte ({len(points)} points) : est-ce bien le parcours complet ?')
            continue
        sans_alt = sum(1 for p in points if p[2] is None)
        if sans_alt > len(points) * 0.2:
            j.erreur(ou, 'altitudes absentes : impossible de simuler. Demander une autre trace, ou la passer dans un outil qui ajoute l\'altitude.')
            continue
        if nature == 'route':
            j.info(ou, 'fichier en itinéraire (rte) : converti en trace (trk).')
        # altitudes manquantes isolées : reprises du point précédent
        alt_brutes, prec = [], next((p[2] for p in points if p[2] is not None), 0.0)
        for p in points:
            prec = p[2] if p[2] is not None else prec
            alt_brutes.append(prec)
        pts = [(p[0], p[1], a_) for p, a_ in zip(points, alt_brutes)]
        t = calculer_trace(pts)
        if t['sauts']:
            j.alerte(ou, f'{t["sauts"]} saut(s) GPS de plus de 200 m corrigés : vérifier la trace sur une carte.')
        ecart_d = (t['distance_km'] - c['distance_km']) / c['distance_km']
        ligne = {'annonce_km': c['distance_km'], 'trace_km': t['distance_km'], 'ecart_km': ecart_d,
                 'annonce_dplus': c.get('dplus_m'), 'trace_dplus': t['dplus_m'], 'ecart_dplus': None}
        if abs(ecart_d) > ECART_DIST_ERREUR:
            proche = min(courses.values(), key=lambda x: abs(x['distance_km'] - t['distance_km']))
            conseil = f' Cette trace correspond plutôt à « {proche["nom"]} » ({fr_nombre(proche["distance_km"], 1)} km).' if proche['id'] != role else ''
            j.erreur(ou, f'trace de {fr_nombre(t["distance_km"], 1)} km pour {fr_nombre(c["distance_km"], 1)} km annoncés ({ecart_d:+.0%}).{conseil}')
            controles[ou] = ligne
            continue
        if abs(ecart_d) > ECART_DIST_ALERTE:
            j.alerte(ou, f'distance de la trace {fr_nombre(t["distance_km"], 1)} km pour {fr_nombre(c["distance_km"], 1)} km annoncés ({ecart_d:+.0%}).')
        if c.get('dplus_m'):
            ecart_p = (t['dplus_m'] - c['dplus_m']) / c['dplus_m']
            ligne['ecart_dplus'] = ecart_p
            if abs(ecart_p) > ECART_DPLUS_ERREUR:
                j.erreur(ou, f'D+ de la trace {fr_nombre(t["dplus_m"])} m pour {fr_nombre(c["dplus_m"])} m annoncés ({ecart_p:+.0%}) : mauvaise trace ou altitudes faussées.')
                controles[ou] = ligne
                continue
            if abs(ecart_p) > ECART_DPLUS_ALERTE:
                j.alerte(ou, f'D+ de la trace {fr_nombre(t["dplus_m"])} m pour {fr_nombre(c["dplus_m"])} m annoncés ({ecart_p:+.0%}).')
        else:
            j.info(ou, f'D+ non annoncé : {fr_nombre(t["dplus_m"])} m d\'après la trace.')
        controles[ou] = ligne
        ravitos = ravitos_depuis_wpts(pts, t['cumul'], wpts)
        if not ravitos and c.get('ravitos'):
            ravitos = sorted(({'km': float(r['km']), 'nom': str(r.get('nom', ''))[:60]} for r in c['ravitos']
                              if 0 < float(r['km']) < t['distance_km']), key=lambda r: r['km'])
            j.info(ou, f'{len(ravitos)} ravito(s) repris du lot et ajoutés à la trace.')
        elif not ravitos:
            j.alerte(ou, 'aucun ravito dans le fichier ni dans le lot : le coureur devra les saisir.')
        boucle = haversine(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1]) < 500
        nom_gpx = f'{ev_id}__{role}.gpx'
        if not a.simuler:
            ecrire_gpx(sortie / nom_gpx, f'{ev["nom"]} · {c["nom"]}', pts, alt_brutes, ravitos, t['cumul'])
            produits.append(sortie / nom_gpx)
        c['gpx'] = nom_gpx
        c['ravitos'] = ravitos
        c['trace'] = {
            'distance_km': round(t['distance_km'], 2), 'dplus_m': int(round(t['dplus_m'])),
            'dmoins_m': int(round(t['dmoins_m'])), 'alt_min': int(round(t['alt_min'])),
            'alt_max': int(round(t['alt_max'])), 'boucle': boucle,
            'depart': [round(pts[0][0], 5), round(pts[0][1], 5)],
            'profil': profil(t['cumul'], t['alt']), 'integre_le': aujourdhui.isoformat(),
        }

    # ── 4. Mise en forme et tri ─────────────────────────────────
    def cle_tri(e):
        d = e.get('date_debut') or '9999-12'
        # un événement dont seul le mois est connu se range en fin de mois
        return ((fin_de_periode(d) if len(d) == 7 else debut_de_periode(d)), e['nom'])
    propres = []
    for ev in sorted(catalogue['evenements'], key=cle_tri):
        courses = sorted(ev.get('courses', []), key=lambda c: -c['distance_km'])
        ev['courses'] = [{k: c.get(k) for k in CHAMPS_COURSE if c.get(k) is not None} for c in courses]
        propres.append({k: ev.get(k) for k in CHAMPS_EVENEMENT if ev.get(k) is not None})
    catalogue['evenements'] = propres
    change = json.dumps(catalogue, sort_keys=True, ensure_ascii=False) != avant or bool(produits)
    if change:
        catalogue['maj'] = aujourdhui.isoformat()
    catalogue['version'] = 1

    # ── 5. Prochaines traces attendues ──────────────────────────
    attendues = []
    for ev in catalogue['evenements']:
        deb = debut_de_periode(ev.get('date_debut'))
        if deb and deb <= aujourdhui + dt.timedelta(days=92):
            manquantes = [c['nom'] for c in ev['courses'] if not c.get('gpx')]
            if manquantes:
                attendues.append((ev, manquantes))

    # ── 6. Écriture ─────────────────────────────────────────────
    bloque = bool(j.erreurs) and not a.forcer
    a_televerser, a_supprimer = [], []
    if not a.simuler and not bloque:
        dossier_cat.mkdir(parents=True, exist_ok=True)
        fichier_cat.write_text(json.dumps(catalogue, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        a_televerser.append(fichier_cat)
        for f in produits:
            shutil.copyfile(f, dossier_cat / f.name)
            a_televerser.append(dossier_cat / f.name)
        sitemap = depot / 'sitemap.xml'
        if sitemap.exists():
            maj_sitemap(sitemap, catalogue)
            a_televerser.append(sitemap)
        for ev in retires:
            for f in sorted(dossier_cat.glob(f'{ev["id"]}__*')):
                a_supprimer.append(f)
        if paquet.exists():
            shutil.rmtree(paquet)
        for f in a_televerser:
            rel = f.relative_to(depot)
            (paquet / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, paquet / rel)

    shutil.rmtree(sortie, ignore_errors=True)
    rapport = ecrire_rapport(depot, catalogue, j, controles, attendues, a_televerser, a_supprimer, retires,
                             a_verifier, lot, aujourdhui, a.simuler, bloque)
    print(rapport)
    if not a.simuler:
        dossier_rap = depot / 'outils' / 'catalogue' / 'rapports'
        dossier_rap.mkdir(parents=True, exist_ok=True)
        (dossier_rap / f'rapport-{aujourdhui.isoformat()}.md').write_text(rapport, encoding='utf-8')
    sys.exit(1 if j.erreurs else 0)


def maj_sitemap(chemin, catalogue):
    txt = chemin.read_text(encoding='utf-8')
    debut, fin = '  <!-- catalogue:debut -->', '  <!-- catalogue:fin -->'
    lm = catalogue.get('maj') or dt.date.today().isoformat()
    urls = [f'  <url>\n    <loc>{SITE}/pages/catalogue.html</loc>\n    <lastmod>{lm}</lastmod>\n    <priority>0.8</priority>\n  </url>']
    for ev in catalogue['evenements']:
        urls.append(f'  <url>\n    <loc>{SITE}/pages/evenement.html?id={ev["id"]}</loc>\n    <lastmod>{lm}</lastmod>\n    <priority>0.6</priority>\n  </url>')
    bloc = debut + '\n' + '\n'.join(urls) + '\n' + fin
    if debut in txt and fin in txt:
        a, b = txt.index(debut), txt.index(fin) + len(fin)
        txt = txt[:a] + bloc + txt[b:]
    else:
        txt = txt.replace('</urlset>', bloc + '\n</urlset>')
    chemin.write_text(txt, encoding='utf-8')


def ecrire_rapport(depot, cat, j, controles, attendues, a_televerser, a_supprimer, retires, a_verifier,
                   lot, aujourdhui, simuler, bloque):
    evs = cat['evenements']
    n_courses = sum(len(e['courses']) for e in evs)
    n_gpx = sum(1 for e in evs for c in e['courses'] if c.get('gpx'))
    L = [f'# Catalogue des courses : rapport du {aujourdhui.strftime("%d/%m/%Y")}', '']
    if lot:
        L.append(f'Lot appliqué : {lot.get("lot", "?")} ({len(lot.get("evenements", []))} propositions).')
    L.append(f'Catalogue : {len(evs)} événements, {n_courses} courses, {n_gpx} traces GPX, '
             f'{sum(1 for e in evs if e.get("photo"))} photos, {sum(1 for e in evs if e.get("logo"))} logos.')
    L.append(f'Encore à vérifier : {sum(1 for e in evs if e.get("statut") != "verifie")} événements '
             '(passer « statut » à « verifie » une fois les infos confirmées sur le site officiel).')
    if simuler:
        L.append('\n**Contrôle seul (--simuler) : rien n\'a été écrit.**')
    elif bloque:
        L.append('\n**Erreurs bloquantes : rien n\'a été écrit. Corriger puis relancer.**')
    L.append('')
    if j.erreurs:
        L += ['## Erreurs à corriger', ''] + [f'- **{o}** : {m}' for o, m in j.erreurs] + ['']
    if j.alertes:
        L += ['## Points à regarder', ''] + [f'- **{o}** : {m}' for o, m in j.alertes] + ['']
    if controles:
        L += ['## Traces contrôlées', '', '| Course | Annoncé | Trace | Écart |', '|---|---|---|---|']
        for ou, c in controles.items():
            ann = f'{fr_nombre(c["annonce_km"], 1)} km' + (f' · {fr_nombre(c["annonce_dplus"])} m' if c['annonce_dplus'] else '')
            tr = f'{fr_nombre(c["trace_km"], 1)} km · {fr_nombre(c["trace_dplus"])} m'
            ec = f'{c["ecart_km"]:+.0%}' + (f' · {c["ecart_dplus"]:+.0%}' if c['ecart_dplus'] is not None else '')
            L.append(f'| {ou} | {ann} | {tr} | {ec} |')
        L.append('')
    if a_verifier:
        L += ['## À vérifier sur les sites officiels', '']
        for ev_id, items in a_verifier.items():
            L.append(f'- **{ev_id}**')
            L += [f'  - {x}' for x in items]
        L.append('')
    if attendues:
        L += ['## Traces attendues (événements des trois prochains mois)', '']
        for ev, manquantes in attendues:
            dispo = f' (publication annoncée le {ev["gpx_disponible_le"]})' if ev.get('gpx_disponible_le') else ''
            L.append(f'- **{ev["nom"]}** ({ev["id"]}){dispo} : ' + ', '.join(manquantes))
            ids = [c['id'] for c in ev['courses'] if not c.get('gpx')]
            L.append('  - noms de fichiers : ' + ', '.join(f'`{ev["id"]}__{i}.gpx`' for i in ids))
        L.append('')
    if retires:
        L += ['## Retirés du catalogue', ''] + [f'- {e["nom"]} ({e["id"]})' for e in retires] + ['']
    if a_televerser:
        L += ['## Fichiers à téléverser sur GitHub', '',
              'Ils sont rassemblés dans `outils/catalogue/a-televerser/`, rangés comme dans le dépôt.', '']
        L += [f'- `{f.relative_to(depot)}`' for f in a_televerser] + ['']
    if a_supprimer:
        L += ['## Fichiers à supprimer du dépôt', ''] + [f'- `{f.relative_to(depot)}`' for f in a_supprimer] + ['']
    if j.infos:
        L += ['## Informations', ''] + [f'- {o} : {m}' for o, m in j.infos] + ['']
    return '\n'.join(L)


if __name__ == '__main__':
    main()
