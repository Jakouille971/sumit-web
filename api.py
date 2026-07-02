# ══════════════════════════════════════════════════════════════
#  SUM'IT — API Backend FastAPI
#  Lance avec : python api.py
# ══════════════════════════════════════════════════════════════

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import gpxpy
import pandas as pd
import numpy as np
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Auth + BDD
from db import init_db, get_db, User, Profile, Activity, ProfilSnapshot, BilanResultat
from auth import (
    construire_url_google_auth,
    echanger_code_google,
    upsert_user_google,
    creer_jwt,
    get_current_user,
    FRONTEND_URL,
)
from strava import (
    construire_url_strava_auth,
    echanger_code_strava,
    sauvegarder_tokens_strava,
    lister_activites_strava,
    telecharger_gpx_strava,
)

app = FastAPI(title="SUM'IT API", version="1.0.0")

# ── CORS complet ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })

# ══════════════════════════════════════════════════════════════
#  CONSTANTES
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  FACTEUR D'ÉQUIVALENCE-PENTE (≠ Minetti pur)
# ══════════════════════════════════════════════════════════════
# Ce facteur convertit vitesse réelle ↔ vitesse-équivalente-plat :
#   - à l'analyse : vep = vitesse_réelle × facteur
#   - à la simulation : vitesse = vep / facteur
#
# ⚠️ Ce n'est PAS la courbe de coût énergétique de Minetti (2002).
# C'est un facteur d'équivalence-EFFORT maison, inspiré de Minetti mais
# volontairement divergent, qui combine deux réalités du trail :
#   • en MONTÉE : coût métabolique (proche de Minetti, un peu amorti au-delà de +20%)
#   • en DESCENTE : coût MUSCULAIRE/TECHNIQUE du freinage excentrique (quadriceps),
#     pas le coût métabolique. C'est pourquoi la courbe descendante fait un "U" :
#     descendre en pente douce (~-10%) coûte moins que le plat (creux à 0.80),
#     mais la descente raide redevient coûteuse à cause du freinage et de la
#     technique (remontée jusqu'à 1.12 à -25%), sans atteindre les valeurs
#     extrêmes de l'ancienne table.
#
# Ces valeurs sont à recalibrer sur des splits réels (fichiers FIT avec
# temps de passage par section) quand ils seront disponibles.
FACTEUR_EQUIVALENCE_PENTE = {
    -25:1.12,-20:1.00,-15:0.88,-10:0.80,
    -5:0.85,0:1.00,5:1.40,10:1.90,
    15:2.40,20:2.70,25:3.20
}

# Alias rétro-compatible (déprécié, à retirer après migration complète)
MINETTI_TABLE = FACTEUR_EQUIVALENCE_PENTE

VEP_MAX = {
    'montee_raide':12.0,'montee_soutenue':13.0,'montee_douce':14.0,
    'plat':20.0,'descente_douce':16.0,'descente_soutenue':14.0,'descente_raide':12.0,
}

REF_VEP = {
    'montee_raide':6.5,'montee_soutenue':7.0,'montee_douce':7.5,'plat':9.0,
    'descente_douce':8.5,'descente_soutenue':7.5,'descente_raide':6.5,
}

ORDRE_TERRAINS = [
    'montee_raide','montee_soutenue','montee_douce','plat',
    'descente_douce','descente_soutenue','descente_raide'
]

CATEGORIES = [
    {'nom':'Court', 'emoji':'🟢','min':0, 'max':25, 'facteur':1.15},
    {'nom':'Moyen', 'emoji':'🔵','min':25,'max':50, 'facteur':1.00},
    {'nom':'Long',  'emoji':'🟠','min':50,'max':80, 'facteur':0.88},
    {'nom':'Ultra', 'emoji':'🔴','min':80,'max':999,'facteur':0.78},
]

POIDS_TYPE = {'course':1.00,'resultat':1.00,'rando':1.00,'entrainement':0.70,'sortie':0.40}
DEMI_VIE   = 180

# Bornes du coefficient course (source unique pour éviter les divergences)
COEF_MIN = 1.00
COEF_MAX = 1.40

ZONES_FC = {
    1:{'min':0.00,'max':0.65,'drain_h':0.02},
    2:{'min':0.65,'max':0.75,'drain_h':0.05},
    3:{'min':0.75,'max':0.85,'drain_h':0.10},
    4:{'min':0.85,'max':0.95,'drain_h':0.18},
    5:{'min':0.95,'max':1.00,'drain_h':0.30},
}

# ══════════════════════════════════════════════════════════════
#  FONCTIONS DE BASE
# ══════════════════════════════════════════════════════════════

def dist_gps(lat1,lon1,lat2,lon2):
    R=6371000
    p1,p2=np.radians(lat1),np.radians(lat2)
    dp,dl=np.radians(lat2-lat1),np.radians(lon2-lon1)
    a=np.sin(dp/2)**2+np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def terrain(p):
    if p>=15:  return 'montee_raide'
    elif p>=8: return 'montee_soutenue'
    elif p>=3: return 'montee_douce'
    elif p>=-3:return 'plat'
    elif p>=-8:return 'descente_douce'
    elif p>=-15:return 'descente_soutenue'
    else:      return 'descente_raide'

def gap_factor(p):
    """
    Facteur d'équivalence-pente (Grade Adjusted Pace maison) à la pente p (en %).
    Interpole linéairement dans FACTEUR_EQUIVALENCE_PENTE.
    Voir le commentaire de FACTEUR_EQUIVALENCE_PENTE : ce n'est pas du Minetti pur.
    """
    pc=max(-25,min(25,p))
    ks=sorted(FACTEUR_EQUIVALENCE_PENTE.keys())
    for i in range(len(ks)-1):
        p1,p2=ks[i],ks[i+1]
        if p1<=pc<=p2:
            t=(pc-p1)/(p2-p1)
            return FACTEUR_EQUIVALENCE_PENTE[p1]+t*(FACTEUR_EQUIVALENCE_PENTE[p2]-FACTEUR_EQUIVALENCE_PENTE[p1])
    return 1.0

# Alias rétro-compatible (déprécié)
minetti = gap_factor

def facteur_endurance(dist_km):
    """
    Facteur d'endurance CONTINU en fonction de la distance (loi de puissance).
    Remplace les anciens paliers discrets qui créaient une discontinuité
    artificielle (~13 % de saut entre une course de 24 km et une de 26 km).

    Calé sur les points de référence historiques :
      12 km → ~1.19 | 37 km → ~0.96 | 65 km → ~0.87 | 100 km → ~0.79 | 160 km → ~0.72
    Plus la distance est longue, plus le facteur baisse (gestion de l'effort,
    ralentissement inévitable sur ultra).
    """
    d = max(3.0, min(300.0, float(dist_km)))
    return 1.9220 * (d ** -0.1935)

def categorie(dist_km):
    """
    Renvoie la catégorie de distance pour l'AFFICHAGE (nom + emoji) et le
    facteur d'endurance CONTINU (plus de saut aux frontières).
    Le champ 'facteur' est désormais calculé en continu via facteur_endurance().
    """
    # Nom/emoji pour l'affichage (les bornes ne servent qu'au libellé)
    for c in CATEGORIES:
        if c['min'] <= dist_km < c['max']:
            base = c
            break
    else:
        base = CATEGORIES[-1]
    # On renvoie une copie avec le facteur continu
    return {
        'nom': base['nom'],
        'emoji': base['emoji'],
        'min': base['min'],
        'max': base['max'],
        'facteur': round(facteur_endurance(dist_km), 4),
    }

def zone_fc(fc,fcmax):
    r=fc/fcmax
    if r<0.65:return 1
    elif r<0.75:return 2
    elif r<0.85:return 3
    elif r<0.95:return 4
    else:return 5

def poids_temp(date):
    if date is None: return 0.5
    now=datetime.now(timezone.utc)
    if date.tzinfo is None: date=date.replace(tzinfo=timezone.utc)
    j=max(0,(now-date).days)
    return max(0.10,np.exp(-np.log(2)*j/DEMI_VIE))

def fmt(s):
    s=max(0,int(s))
    return f"{s//3600}h{(s%3600)//60:02d}m{s%60:02d}s"

# ══════════════════════════════════════════════════════════════
#  CHARGEMENT GPX
# ══════════════════════════════════════════════════════════════

def charger_gpx(data_bytes, fcmax=193):
    txt=data_bytes.decode('utf-8',errors='replace')
    gpx=gpxpy.parse(txt)
    if not gpx.tracks:
        raise ValueError("Aucune trace GPX trouvée")

    pts=[]
    date0=None
    for seg in gpx.tracks[0].segments:
        for pt in seg.points:
            if date0 is None and pt.time: date0=pt.time
            fc=None
            if pt.extensions:
                for ext in pt.extensions:
                    for ch in ext:
                        if ch.tag.split('}')[-1].lower()=='hr':
                            try: fc=int(ch.text)
                            except: pass
            pts.append({
                'lat':pt.latitude,'lon':pt.longitude,
                'alt':pt.elevation or 0,'t':pt.time,'fc':fc
            })

    if len(pts)<10: raise ValueError("Fichier GPX trop court")

    df=pd.DataFrame(pts)
    df['dist_m']=0.0
    for i in range(1,len(df)):
        df.loc[i,'dist_m']=dist_gps(
            df.loc[i-1,'lat'],df.loc[i-1,'lon'],
            df.loc[i,'lat'],  df.loc[i,'lon']
        )

    a_timestamps = df['t'].notna().any()
    df['duree_s']=df['t'].diff().dt.total_seconds().fillna(0) if a_timestamps else 1.0

    # ── Clamp de la distance à un plafond physique ──
    # Un saut GPS (perte de signal, tunnel, réflexion) peut créer une distance
    # aberrante entre deux points. Sans correction, elle pollue dist_cum (distance
    # totale → temps prédit) ET la pente locale. On plafonne dist_m à la distance
    # maximale physiquement possible : VIT_MAX_MS × dt.
    #
    # ⚠️ On n'applique ce clamp QUE si la trace a de vrais timestamps. Pour une
    # trace de PARCOURS (planification, sans <time>), duree_s vaut 1s par défaut
    # et le plafond tronquerait à tort les points légitimement espacés (>8 m).
    VIT_MAX_MS = 8.0  # 8 m/s ≈ 28.8 km/h : vitesse de pointe plausible en trail/descente
    if a_timestamps:
        plafond = (df['duree_s'] * VIT_MAX_MS).clip(lower=0)
        # Là où le temps est nul (points dupliqués), on garde un plafond large
        plafond = plafond.replace(0, np.nan).fillna(df['dist_m'].median() * 3 if df['dist_m'].median() > 0 else 50)
        df['dist_m'] = df['dist_m'].clip(upper=plafond)

    df['vit_kmh']=(df['dist_m']/df['duree_s'].replace(0,np.nan)*3.6).clip(0,40).fillna(0)

    # ── Lissage altitude : moins agressif pour préserver le D+ réel ──
    # L'ancien double lissage médiane(15)+moyenne(30) écrasait les micro-reliefs
    # et sous-estimait le D+ de 10-20 % vs le D+ officiel des courses.
    # On garde une médiane courte (élimine les outliers GPS ponctuels) suivie
    # d'une moyenne courte (lissage doux), ce qui conserve mieux le dénivelé réel.
    df['alt']=df['alt'].rolling(7,center=True,min_periods=1).median()
    df['alt']=df['alt'].rolling(11,center=True,min_periods=1).mean()
    df['dz']=df['alt'].diff().fillna(0)

    # ── Comptage du D+/D- par HYSTÉRÉSIS (seuil cumulé, pas par point) ──
    # ⚠️ NE PAS seuiller chaque dz individuellement : sur une trace enregistrée
    # à 1 point/seconde, chaque montée légitime vaut ~0,2 m par point. Un seuil
    # par point (dz >= 0,5 m) mettait alors 100 % des incréments à zéro et
    # écrasait le D+ (bug : 1720 m → 8 m). On accumule donc la variation et on
    # ne valide un gain/perte qu'une fois franchi un seuil cumulé (SEUIL_DZ),
    # ce qui filtre le bruit du capteur SANS détruire le dénivelé réel.
    SEUIL_DZ = 2.0  # mètres de variation cumulée avant de valider un segment
    alt_vals = df['alt'].values
    dp_arr = np.zeros(len(alt_vals))
    dm_arr = np.zeros(len(alt_vals))
    if len(alt_vals) > 1:
        ref = alt_vals[0]          # altitude de référence du segment courant
        sens = 0                   # +1 montée, -1 descente, 0 indéterminé
        for i in range(1, len(alt_vals)):
            delta = alt_vals[i] - ref
            if sens >= 0 and delta >= SEUIL_DZ:
                # On valide une montée cumulée
                dp_arr[i] = delta
                ref = alt_vals[i]; sens = 1
            elif sens <= 0 and delta <= -SEUIL_DZ:
                # On valide une descente cumulée
                dm_arr[i] = -delta
                ref = alt_vals[i]; sens = -1
            elif (sens > 0 and delta < 0) or (sens < 0 and delta > 0):
                # Changement de direction : on repart de ce point
                ref = alt_vals[i-1]
                # Réévalue immédiatement le delta depuis le nouveau ref
                delta2 = alt_vals[i] - ref
                if delta2 >= SEUIL_DZ:
                    dp_arr[i] = delta2; ref = alt_vals[i]; sens = 1
                elif delta2 <= -SEUIL_DZ:
                    dm_arr[i] = -delta2; ref = alt_vals[i]; sens = -1
                else:
                    sens = 0
    df['dp'] = dp_arr
    df['dm'] = dm_arr

    # ── Filtrage outliers de vitesse (3 sigma) ──
    # Élimine les points avec une vitesse aberrante (perte GPS, tunnel...)
    if len(df) > 50:
        v_med = df['vit_kmh'].median()
        v_std = df['vit_kmh'].std()
        seuil_max = v_med + 3 * v_std
        df.loc[df['vit_kmh'] > seuil_max, 'vit_kmh'] = np.nan
        df['vit_kmh'] = df['vit_kmh'].interpolate().fillna(v_med)

    # ── Distance cumulée totale : calculée AVANT tout filtrage ──
    # ⚠️ Le filtre des arrêts (ci-dessous) retire des points, mais leur distance
    # NE DOIT PAS disparaître du cumul (sinon la distance totale est sous-estimée,
    # ~10 % de perte en trail où l'on passe beaucoup de temps sous 1 km/h en
    # montée raide). On fige donc la distance cumulée réelle ici, sur tous les
    # points, avant d'exclure les arrêts pour le calcul des allures.
    df['dist_cum']=df['dist_m'].cumsum()/1000

    # Exclure les arrêts UNIQUEMENT pour le calcul des allures/VEP (pas la distance).
    # Un arrêt = vitesse < 1 km/h. On ne les retire pas du DataFrame (ça amputerait
    # la distance) : on neutralise leur contribution aux allures en les marquant.
    df['est_arret'] = (df['vit_kmh'] < 1.0) & (df['duree_s'] > 0)

    df['pente']=(df['dz']/df['dist_m'].replace(0,np.nan)*100).replace([np.inf,-np.inf],0).fillna(0).clip(-80,80)
    df['pente_l']=df['pente'].rolling(10,center=True).mean().fillna(df['pente'])
    df['terrain']=df['pente_l'].apply(terrain)
    df['cm']=df['pente_l'].apply(gap_factor)
    df['vep']=(df['vit_kmh']*df['cm']).clip(0,20)
    df['vep']=df.apply(lambda r:min(r['vep'],VEP_MAX.get(r['terrain'],18)),axis=1)
    # Les points d'arrêt ne comptent pas dans le lissage des VEP (allure faussée)
    df.loc[df['est_arret'], 'vep'] = np.nan
    df['vep']=df['vep'].rolling(15,center=True,min_periods=1).mean()
    # Combler les NaN résiduels (arrêts en bord de série sans voisin valide)
    df['vep']=df['vep'].ffill().bfill().fillna(0)

    df['t_h']=df['duree_s'].cumsum()/3600
    df['dep_m']=df['dist_m']*df['cm']
    df['dep_cum']=df['dep_m'].cumsum()/1000
    df['dp_cum']=df['dp'].cumsum()
    df['dm_cum']=df['dm'].cumsum()

    nb_fc=int(df['fc'].notna().sum())
    if nb_fc>50:
        df['fc']=df['fc'].interpolate().rolling(10,center=True,min_periods=1).mean()
        df['fc_r']=(df['fc']/fcmax).clip(0,1)
        df['z_fc']=df['fc'].apply(lambda x:zone_fc(x,fcmax) if pd.notna(x) else 3)
        df['drain']=df['z_fc'].apply(lambda z:ZONES_FC.get(int(z),ZONES_FC[3])['drain_h']/3600)
    else:
        df['fc_r']=np.nan
        df['z_fc']=3
        df['drain']=0.05/3600

    return df.reset_index(drop=True), date0, nb_fc

# ══════════════════════════════════════════════════════════════
#  ANALYSE D'UNE TRACE
# ══════════════════════════════════════════════════════════════

def analyser_trace(df, date0, type_sortie, fcmax, types_terrain=None):
    """
    Analyse d'une trace GPX.
    Le paramètre types_terrain est conservé pour compatibilité mais n'est plus
    utilisé pour normaliser la VEP — la technicité reste une info d'affichage
    sans impact sur le calcul du profil.
    """
    dist_km=float(df['dist_cum'].max())
    dep_km =float(df['dep_cum'].max())
    duree_h=float(df['t_h'].max())
    dplus_m=float(df['dp_cum'].max())
    cat=categorie(dist_km)
    pt=poids_temp(date0)
    ptype=POIDS_TYPE.get(type_sortie,0.7)
    ptot=pt*ptype

    dep_tot=df['dep_m'].sum()
    df=df.copy()
    df['eff']=df['dep_m'].cumsum()/dep_tot*100 if dep_tot>0 else 0

    scores={}
    for t in ORDRE_TERRAINS:
        sub=df[df['terrain']==t]
        # Seuil abaissé de 20 à 8 points : sur une sortie peu vallonnée, exiger
        # 20 points par type de terrain écartait à tort les montées/descentes,
        # ce qui faussait l'archétype (ex : "Descendeur" par défaut faute de
        # données de montée). 8 points suffisent pour une médiane stable.
        if len(sub)<8: continue
        vb=float(sub['vep'].median())
        vn=vb/cat['facteur']
        tr=[]
        for s in range(0,100,20):
            tt=sub[(sub['eff']>=s)&(sub['eff']<s+20)]
            if len(tt)>=5: tr.append(float(tt['vep'].median()))
        cv=float(np.std(tr)/np.mean(tr)) if len(tr)>=2 and np.mean(tr)>0 else 0.10
        scores[t]={
            'vep_brute':round(vb,2),'vep_norm':round(vn,2),
            'dist_km':round(float(sub['dist_m'].sum()/1000),2),'cv':round(cv,4)
        }

    drain_h=float(df['drain'].sum()/duree_h) if duree_h>0 else 0.08
    fc_med=float(df['fc_r'].median()) if df['fc_r'].notna().any() else None

    zd={}
    if df['z_fc'].notna().any():
        z=df.groupby('z_fc')['duree_s'].sum()
        tot=float(z.sum())
        if tot>0: zd={int(k):round(float(v/tot*100),1) for k,v in z.items()}

    return {
        'dist_km':round(dist_km,2),'dep_km':round(dep_km,2),
        'duree_h':round(duree_h,3),'dplus_m':round(dplus_m,0),
        'categorie':cat['nom'],'type_sortie':type_sortie,
        'poids_temporel':round(pt,3),'poids_type':round(ptype,2),'poids_total':round(ptot,3),
        'scores_terrain':scores,'drain_moy_h':round(drain_h,4),
        'fc_ratio_moy':round(fc_med,3) if fc_med else None,
        'zones_fc':zd,'vep_globale':round(dep_km/duree_h,2) if duree_h>0 else 0,
    }

# ══════════════════════════════════════════════════════════════
#  COEFFICIENT COURSE / ENTRAÎNEMENT
# ══════════════════════════════════════════════════════════════

def coeff_course(traces, cible=0.87):
    """
    Calcul du coefficient course/entraînement basé sur la fréquence cardiaque.

    Améliorations v1.1 :
    - Prise en compte du FC drift (dérive cardiaque sur la durée)
      Sur une longue sortie, la FC dérive vers le haut à effort constant
      → on prend la médiane du premier tiers (FC stabilisée mais pas dérivée)
    - Pondération par la durée (sortie longue = plus représentative)
    - Compensation pour les sorties très courtes (< 30 min) où le FC
      n'a pas le temps de se stabiliser
    """
    fe,pe,fc_,pc=[],[],[],[]
    for t in traces:
        r=t.get('fc_ratio_moy')
        if r is None: continue
        d=t['dist_km']
        duree=t.get('duree_h',1)

        # Pondération par durée : plus longue = plus représentative
        # Mais on plafonne à 4h pour pas écraser les courses courtes
        poids_duree = min(duree, 4.0)

        # Compensation sortie courte : FC pas stabilisée, on minore son poids
        if duree < 0.5:  # moins de 30 min
            poids_duree *= 0.5

        poids = d * poids_duree

        if t['type_sortie']=='entrainement':
            fe.append(r); pe.append(poids)
        elif t['type_sortie'] in ('course', 'resultat'):
            fc_.append(r); pc.append(poids)

    me=float(np.average(fe,weights=pe)) if fe else 0.75
    mc=float(np.average(fc_,weights=pc)) if fc_ else cible
    c=float(max(COEF_MIN,min(COEF_MAX,mc/me if me>0 else 1.10)))

    return {
        'coefficient':round(c,3),
        'gain_pct':round((c-1)*100,1),
        'fc_moy_entrainement':round(me,3),
        'fc_course_utilisee':round(mc,3),
        'nb_entrainements':len(fe),
        'nb_courses_reelles':len(fc_),
        'calibre_sur_courses':len(fc_)>0,
        'methode':'FC réelle des courses' if len(fc_)>0 else f'Cible générique {int(cible*100)}% FCmax',
    }

# ══════════════════════════════════════════════════════════════
#  AGRÉGATION PROFIL
# ══════════════════════════════════════════════════════════════

def agreger(traces):
    profil={}

    # Étape 1 : agrégation des VEP par terrain
    for t in ORDRE_TERRAINS:
        vs,ps,cs=[],[],[]
        for tr in traces:
            if t not in tr['scores_terrain']: continue
            st=tr['scores_terrain'][t]
            vs.append(st['vep_norm'])
            ps.append(st['dist_km']*tr['poids_total'])
            cs.append(st['cv'])
        if not vs: continue
        va=float(np.average(vs,weights=ps))
        cm=float(np.mean(cs))
        profil[t]={
            'vep_norm':round(va,2),
            'vep_std':round(float(np.std(vs)),2),
            'nb_courses':len(vs),
            'f_basse':round(float(max(0.05,cm*0.8)),3),
            'f_haute':round(float(min(0.30,cm*1.2)),3),
        }

    # ── Combler les terrains manquants par interpolation ──
    # Si un type de terrain n'a aucune donnée (ex : aucune montée raide dans les
    # traces), le laisser absent fausse l'archétype (qui ne "voit" alors que les
    # terrains présents → bascule artificielle vers Descendeur/Grimpeur).
    # On estime la VEP manquante depuis les terrains voisins via un facteur
    # physiologique de référence (REF_VEP), pour garder un profil complet.
    presents = [t for t in ORDRE_TERRAINS if t in profil]
    if presents:
        # Niveau global du coureur : ratio moyen entre sa VEP et la VEP de référence
        ratios = []
        for t in presents:
            ref = REF_VEP.get(t, 7.5)
            if ref > 0:
                ratios.append(profil[t]['vep_norm'] / ref)
        niveau = float(np.median(ratios)) if ratios else 1.0
        # Moyenne des incertitudes pour les terrains comblés
        cm_moy = float(np.mean([ (profil[t]['f_basse']+profil[t]['f_haute'])/2 for t in presents ]))

        for t in ORDRE_TERRAINS:
            if t not in profil:
                # VEP estimée = niveau du coureur × VEP de référence du terrain
                vep_est = round(REF_VEP.get(t, 7.5) * niveau, 2)
                profil[t] = {
                    'vep_norm': vep_est,
                    'vep_std': 0.0,
                    'nb_courses': 0,
                    'f_basse': round(max(0.05, cm_moy*0.9), 3),
                    'f_haute': round(min(0.35, cm_moy*1.4), 3),
                    'estime': True,   # marqueur : valeur interpolée, pas mesurée
                }

    # Étape 2 : score de pente = écart % vs VEP plat de l'utilisateur
    # Hypothèse : sur du plat, VEP_user ≈ vitesse réelle. Sur pente,
    # idéalement VEP_user devrait être identique (effort équivalent).
    # → on mesure l'écart : signe + = "tu surperformes sur ce terrain", - = "tu sous-performes"
    if 'plat' in profil:
        vep_plat = profil['plat']['vep_norm']
        for t in profil:
            ecart_pct = round(((profil[t]['vep_norm'] - vep_plat) / vep_plat) * 100, 1)
            profil[t]['ecart_plat_pct'] = ecart_pct
            # Label couleur côté frontend selon signe
            profil[t]['signe'] = '+' if ecart_pct >= 0 else ''
    else:
        # Fallback si pas de données plat
        for t in profil:
            profil[t]['ecart_plat_pct'] = 0
            profil[t]['signe'] = ''

    # Drain agrégé
    drains=[t['drain_moy_h'] for t in traces]
    poids=[t['poids_total'] for t in traces]
    drain=float(np.average(drains,weights=poids)) if drains else 0.08
    return profil, round(drain,4)

# ══════════════════════════════════════════════════════════════
#  ARCHÉTYPE
# ══════════════════════════════════════════════════════════════

def extraire_trackpoints(df, max_points=200):
    """
    Échantillonne les trackpoints du DataFrame pour stockage léger
    (carte Leaflet + altimétrie + comparaison temps). Conserve dist, lat, lon, alt, t.
    """
    if df is None or len(df) == 0:
        return []

    n = len(df)
    step = max(1, n // max_points)
    sample = df.iloc[::step].copy()

    # On ajoute toujours le dernier point
    if sample.index[-1] != df.index[-1]:
        sample = pd.concat([sample, df.iloc[[-1]]])

    cols = {'lat', 'lon', 'alt', 'dist_cum'}
    if not cols.issubset(sample.columns):
        return []

    # Temps cumulé (secondes) si disponible, pour la comparaison réel/prédit
    has_time = 'duree_s' in df.columns
    if has_time:
        t_cum_full = df['duree_s'].cumsum()

    pts = []
    for idx, row in sample.iterrows():
        pt = {
            'lat':  round(float(row['lat']), 6),
            'lon':  round(float(row['lon']), 6),
            'alt':  round(float(row['alt']), 1),
            'dist': round(float(row['dist_cum']), 3),
        }
        if has_time:
            try:
                pt['t'] = round(float(t_cum_full.loc[idx]), 1)
            except Exception:
                pass
        pts.append(pt)
    return pts


def archetype(profil, profil_type='trail'):
    """
    Classifie le coureur en 8 archétypes distincts basés sur :
    - em : écart moyen en montée (positif = à l'aise)
    - ed : écart moyen en descente (positif = à l'aise)
    - sr : régularité (écart-type des écarts → faible = homogène)
    - em_raide / em_douce : profil dans les montées
    - ed_raide / ed_douce : profil dans les descentes

    En rando, les vitesses sont plus basses et plus homogènes : les écarts
    par terrain se compriment, ce qui fausse la détection de spécialisation
    (tout le monde paraît "Cabri"). On durcit donc les seuils et on privilégie
    les archétypes d'endurance/régularité, plus pertinents pour la marche.
    """
    if not profil:
        return {'key':'combattant','nom':'Le Combattant','desc':'Profil en construction.',
                'forces':[],'faiblesses':[],'conseil':'Ajoute plus de traces GPX.'}

    est_rando = (profil_type == 'rando')

    # Écarts par type de terrain
    def ep(t): return profil[t]['ecart_plat_pct'] if t in profil and 'ecart_plat_pct' in profil[t] else None

    em_raide    = ep('montee_raide')
    em_soutenue = ep('montee_soutenue')
    em_douce    = ep('montee_douce')
    ed_douce    = ep('descente_douce')
    ed_soutenue = ep('descente_soutenue')
    ed_raide    = ep('descente_raide')

    tm = [v for v in [em_raide, em_soutenue, em_douce] if v is not None]
    td = [v for v in [ed_douce, ed_soutenue, ed_raide] if v is not None]

    em = float(np.mean(tm)) if tm else 0
    ed = float(np.mean(td)) if td else 0

    ecarts = [profil[t]['ecart_plat_pct'] for t in profil if 'ecart_plat_pct' in profil[t]]
    sr = float(np.std(ecarts)) if ecarts else 100

    # Spécialisation : monté raide >> douce → puissance en haute pente
    delta_raide_mont = (em_raide - em_douce) if em_raide is not None and em_douce is not None else 0
    delta_raide_desc = (ed_raide - ed_douce) if ed_raide is not None and ed_douce is not None else 0

    # ═══ Seuils adaptés au type de profil ═══
    # En rando : seuils de spécialisation plus stricts + régularité plus tolérante,
    # car les écarts sont naturellement plus resserrés.
    if est_rando:
        seuil_delta_raide = 14    # au lieu de 8 : il faut une vraie spécialisation
        seuil_dominance   = 8     # au lieu de 5 : montée vs descente
        seuil_equilibre   = 10    # au lieu de 7 : plus tolérant
        seuil_diesel      = 16    # au lieu de 12
    else:
        seuil_delta_raide = 8
        seuil_dominance   = 5
        seuil_equilibre   = 7
        seuil_diesel      = 12

    # ═══ Classification (ordre = priorité) ═══

    # En rando, on privilégie d'abord les profils d'endurance/régularité
    # (le Marcheur régulier, le Diesel) avant les spécialistes explosifs.
    if est_rando:
        # R1. L'Équilibré — randonneur très régulier sur tous terrains
        if sr < seuil_equilibre:
            return {'key':'equilibre','nom':"L'Équilibré",
                    'desc':"En rando, tu gardes un rythme constant quel que soit le terrain. Solide et prévisible.",
                    'forces':['Régularité sur tous terrains','Gestion du rythme','Endurance longue durée'],
                    'faiblesses':['Pas de point fort marqué'],
                    'conseil':'Travaille un terrain spécifique (montée raide ou descente technique) pour gagner en polyvalence.'}

        # R2. Le Grimpeur — vraiment plus à l'aise en montée (seuil strict)
        if em > 0 and em > ed + seuil_dominance:
            return {'key':'grimpeur','nom':'Le Grimpeur',
                    'desc':"Les montées sont ton terrain. Tu avales le D+ sans faiblir, là où d'autres ralentissent.",
                    'forces':['Montées longues et soutenues',"Résistance à l'accumulation de D+",'Marche en côte efficace'],
                    'faiblesses':['Descentes techniques','Allure sur le plat'],
                    'conseil':'Travaille tes descentes pour ne pas perdre le temps gagné en montée.'}

        # R3. Le Descendeur — vraiment plus à l'aise en descente
        if ed > 0 and ed > em + seuil_dominance:
            return {'key':'descendeur','nom':'Le Descendeur',
                    'desc':"Tu dévales les descentes avec assurance et récupères ce que tu perds à la montée.",
                    'forces':['Descentes fluides et sûres','Gestion des appuis','Économie musculaire en descente'],
                    'faiblesses':['Longues montées','Accumulation de D+'],
                    'conseil':'Intègre des montées régulières pour équilibrer ton profil de randonneur.'}

        # R4. Le Cabri — spécialiste montée raide (seuil très strict en rando)
        if em > 0 and delta_raide_mont > seuil_delta_raide:
            return {'key':'cabri','nom':'Le Cabri',
                    'desc':"Les pentes raides ne te font pas peur : tu y es plus efficace que sur les pentes douces.",
                    'forces':['Pentes raides','Passages techniques montants','Force musculaire'],
                    'faiblesses':['Longues montées régulières','Rythme sur terrain roulant'],
                    'conseil':'Travaille l\'endurance sur de longues sorties à allure constante.'}

        # R5. Le Diesel — randonneur d'endurance, monte en puissance sur la durée
        if sr < seuil_diesel:
            return {'key':'diesel','nom':'Le Diesel',
                    'desc':"Tu démarres tranquillement et tu tiens des heures. L'ultra-rando, c'est ton monde.",
                    'forces':['Endurance sur très longue distance','Régularité du rythme','Gestion énergétique'],
                    'faiblesses':['Passages explosifs','Allure de pointe'],
                    'conseil':'Ajoute quelques sorties plus intenses pour élargir ta palette.'}

        # R6. Le Tenace — randonneur courageux par défaut
        return {'key':'tenace','nom':'Le Tenace',
                'desc':"Tu ne lâches rien. Ta force, c'est la constance et la capacité à enchaîner les heures.",
                'forces':["Gestion de l'effort prolongé",'Mental solide','Constance sur ultra-rando'],
                'faiblesses':['Vitesse de pointe','Sections courtes et rapides'],
                'conseil':'Fais-toi plaisir sur les longues traversées. Varie les terrains pour progresser.'}

    # ═══ TRAIL (logique d'origine) ═══

    # 1. Le Cabri — puissant en montée raide (>> douce)
    if em > 0 and delta_raide_mont > seuil_delta_raide:
        return {'key':'cabri','nom':'Le Cabri',
                'desc':"Tu attaques les pentes raides comme un cabri. Plus ça monte, plus tu accélères.",
                'forces':['Pentes raides courtes','Explosivité musculaire','Sections techniques montantes'],
                'faiblesses':['Longues montées régulières','Gestion de l\'effort sur ultra'],
                'conseil':'Travaille des montées longues à allure constante pour ajouter du diesel à ton explosivité.'}

    # 2. Le Grimpeur — excellent en montée (général), particulièrement soutenu/douce
    if em > 0 and em > ed + seuil_dominance:
        return {'key':'grimpeur','nom':'Le Grimpeur',
                'desc':"Tu avales les D+ comme personne. Les montées sont ton terrain de jeu.",
                'forces':['Montées soutenues et longues',"Résistance à l'accumulation de D+",'Économie d\'énergie en côte'],
                'faiblesses':['Descentes techniques','Manque de vitesse sur plat'],
                'conseil':'Travaille tes descentes en fractionné technique pour ne pas perdre ce que tu gagnes en montée.'}

    # 3. Le Funambule — descente raide >> descente douce (technicien)
    if ed > 0 and delta_raide_desc > seuil_delta_raide:
        return {'key':'funambule','nom':'Le Funambule',
                'desc':"Tu danses sur les descentes techniques. Plus ça plonge, plus tu vas vite.",
                'forces':['Descentes raides et techniques','Pieds véloces','Lecture du terrain'],
                'faiblesses':['Montées prolongées','Plat monotone'],
                'conseil':'Renforce le travail spécifique en côte pour équilibrer ton profil.'}

    # 4. Le Descendeur — excellent en descente (général)
    if ed > 0 and ed > em + seuil_dominance:
        return {'key':'descendeur','nom':'Le Descendeur',
                'desc':"Tu récupères dans les descentes ce que tu perds à la montée.",
                'forces':['Descentes rapides et fluides','Technique sur terrain varié','Gestion impact'],
                'faiblesses':['Montées longues','Accumulation de D+'],
                'conseil':'Intègre des montées spécifiques à tes entraînements (côtes courtes intenses).'}

    # 5. L'Équilibré — variabilité très faible
    if sr < seuil_equilibre:
        return {'key':'equilibre','nom':"L'Équilibré",
                'desc':'Profil homogène sur tous les terrains. Pas de point faible, pas de point fort dominant.',
                'forces':['Polyvalence','Régularité de l\'allure','Adaptable à tous parcours'],
                'faiblesses':['Surclassé par des spécialistes sur leur terrain','Pas de signature'],
                'conseil':'Choisis des parcours variés. Travaille un point fort pour te démarquer.'}

    # 6. Le Diesel — modérément performant partout, mais régulier
    if sr < seuil_diesel and -15 < em < 5 and -15 < ed < 5:
        return {'key':'diesel','nom':'Le Diesel',
                'desc':"Tu démarres calmement et tu finis fort. Ton truc, c'est la durée.",
                'forces':['Endurance sur très longue distance','Régularité','Gestion énergétique'],
                'faiblesses':['Accélérations courtes','Démarrage'],
                'conseil':'Ajoute des séances de seuil pour gagner en puissance maximale.'}

    # 7. Le Rouleur — sous-performance en relief mais plat fort (ex-Explosif)
    if em < -20 and ed < -20:
        return {'key':'rouleur','nom':'Le Rouleur',
                'desc':"Tu es à l'aise sur le plat et les sections roulantes. Le relief te freine.",
                'forces':['Sections rapides','Vitesse de base élevée','Plat et faux-plat'],
                'faiblesses':["Fatigue sur longs D+","Difficulté en altitude",'Descentes techniques'],
                'conseil':'Développe ta puissance en côte avec du fractionné montée 1\'/1\'.'}

    # 8. Le Tenace — par défaut, profil endurant
    return {'key':'tenace','nom':'Le Tenace',
            'desc':"Tu ne lâches jamais. Ta force c'est la régularité dans la durée.",
            'forces':["Gestion de l'effort",'Mental et régularité','Constance sur ultra'],
            'faiblesses':['Vitesse de pointe limitée',"Moins à l'aise sur courte distance"],
            'conseil':'Fais-toi plaisir sur les ultras. Pour les courses courtes, travaille la VMA.'}

# ══════════════════════════════════════════════════════════════
#  SIMULATION
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  TECHNICITÉ DU TERRAIN — via OpenStreetMap (Overpass API)
# ══════════════════════════════════════════════════════════════

# 5 catégories de terrain avec coefficients d'impact sur la vitesse
# (1.0 = neutre, < 1.0 = ralentit, > 1.0 = accélère)
TERRAIN_TYPES = {
    'route': {
        'nom': 'Route',
        'emoji': '🛣',
        'coef_vitesse': 1.10,   # +10% : roulant, prévisible
        'desc': 'Asphalte, route goudronnée',
    },
    'piste': {
        'nom': 'Piste',
        'emoji': '🚵',
        'coef_vitesse': 1.00,   # neutre : piste 4x4, chemin agricole
        'desc': 'Piste large, chemin roulant',
    },
    'sentier_large': {
        'nom': 'Sentier large',
        'emoji': '🥾',
        'coef_vitesse': 0.92,   # -8% : sentier large mais terrain naturel
        'desc': 'Sentier confortable, single-track facile',
    },
    'sentier_montagne': {
        'nom': 'Sentier montagne',
        'emoji': '⛰',
        'coef_vitesse': 0.78,   # -22% : technique, racines, cailloux
        'desc': 'Sentier technique de montagne',
    },
    'hors_trace': {
        'nom': 'Hors-trace',
        'emoji': '🌲',
        'coef_vitesse': 0.65,   # -35% : crêtes, pierriers, hors-piste
        'desc': 'Crête, pierrier, hors-sentier balisé',
    },
}

ORDRE_TERRAIN_TYPES = ['route', 'piste', 'sentier_large', 'sentier_montagne', 'hors_trace']

def classifier_osm_way(tags):
    """
    Classe un way OpenStreetMap dans une des 5 catégories de terrain.
    Utilise les tags : highway, surface, sac_scale, tracktype, smoothness.
    """
    if not tags:
        return 'sentier_large'  # défaut

    highway = tags.get('highway', '')
    surface = tags.get('surface', '')
    sac     = tags.get('sac_scale', '')
    track   = tags.get('tracktype', '')

    # 1. SAC scale (échelle suisse de difficulté) — très fiable en montagne
    if sac in ('mountain_hiking', 'demanding_mountain_hiking'):
        return 'sentier_montagne'
    if sac in ('alpine_hiking', 'demanding_alpine_hiking', 'difficult_alpine_hiking'):
        return 'hors_trace'

    # 2. Routes goudronnées
    if highway in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary',
                   'residential', 'unclassified', 'service', 'living_street'):
        return 'route'
    if surface in ('asphalt', 'paved', 'concrete'):
        return 'route'

    # 3. Pistes
    if highway == 'track':
        if track in ('grade1', 'grade2'):
            return 'piste'
        elif track in ('grade3',):
            return 'sentier_large'
        elif track in ('grade4', 'grade5'):
            return 'sentier_montagne'
        return 'piste'
    if highway in ('cycleway', 'bridleway'):
        return 'piste'

    # 4. Sentiers
    if highway == 'footway':
        return 'sentier_large'
    if highway == 'path':
        # Path = sentier — précision via surface
        if surface in ('rock', 'stone', 'pebblestone'):
            return 'sentier_montagne'
        if surface in ('ground', 'dirt', 'earth', 'grass'):
            return 'sentier_large'
        return 'sentier_large'  # défaut path

    if highway == 'steps':
        return 'sentier_montagne'

    # 5. Défaut : sentier large
    return 'sentier_large'


def requeter_overpass(bbox, timeout=15):
    """
    Récupère tous les ways de type "highway" dans la bounding box.
    bbox = (south, west, north, east)
    """
    south, west, north, east = bbox

    # Requête Overpass QL — récupère tous les highways dans la zone
    query = f"""
    [out:json][timeout:{timeout}];
    (
      way["highway"]({south},{west},{north},{east});
    );
    out tags geom;
    """

    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({'data': query}).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers={'User-Agent': 'SUMIT/1.0'})
        with urllib.request.urlopen(req, timeout=timeout + 5) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('elements', [])
    except Exception as e:
        print(f"⚠️ Overpass API erreur : {e}")
        return []


def classifier_trace_via_osm(df, marge=0.005):
    """
    Pour chaque point de la trace, détermine le type de terrain
    en cherchant le way OSM le plus proche.

    Renvoie une Series avec le type de terrain par point.
    """
    if len(df) < 10:
        return ['sentier_large'] * len(df)

    # Bounding box avec marge
    lats = df['lat'].values
    lons = df['lon'].values
    bbox = (
        float(lats.min()) - marge,
        float(lons.min()) - marge,
        float(lats.max()) + marge,
        float(lons.max()) + marge,
    )

    # Requête Overpass
    ways = requeter_overpass(bbox)

    if not ways:
        # Fallback : pas de données OSM
        return ['sentier_large'] * len(df)

    # Construction d'une structure de recherche rapide
    # Pour chaque way, on a sa geometry (liste de lat/lon) + ses tags
    ways_data = []
    for w in ways:
        geom = w.get('geometry', [])
        tags = w.get('tags', {})
        if len(geom) < 2:
            continue
        type_terrain = classifier_osm_way(tags)
        # Échantillonnage : on garde 1 point sur 2 si geom > 50 points pour perf
        step = max(1, len(geom) // 50)
        for pt in geom[::step]:
            ways_data.append({
                'lat': pt['lat'],
                'lon': pt['lon'],
                'type': type_terrain,
            })

    if not ways_data:
        return ['sentier_large'] * len(df)

    # Pour chaque point GPX, trouver le way le plus proche (KDTree pour perf)
    ways_arr = np.array([(w['lat'], w['lon']) for w in ways_data])
    ways_types = [w['type'] for w in ways_data]

    types = []
    # Subsample du GPX si trop dense (1 point tous les ~10m)
    for i in range(len(df)):
        lat = float(df['lat'].iloc[i])
        lon = float(df['lon'].iloc[i])
        # Distance euclidienne approchée (suffisant pour proximité locale)
        dist_sq = (ways_arr[:, 0] - lat) ** 2 + (ways_arr[:, 1] - lon) ** 2
        idx = int(np.argmin(dist_sq))
        types.append(ways_types[idx])

    # Lissage : on évite les changements brusques en regardant les voisins
    # Si point isolé d'un type différent entre 2 du même type, on l'aligne
    smoothed = list(types)
    for i in range(2, len(types) - 2):
        # Si les 2 voisins (avant + après) sont du même type, on s'aligne
        if types[i-1] == types[i+1] and types[i-1] == types[i-2] and types[i-1] == types[i+2]:
            smoothed[i] = types[i-1]

    return smoothed



def simuler(df, profil, drain_h, cat, coeff=1.0, types_terrain=None):
    """
    Simulation point par point avec modèle de fatigue.

    types_terrain : liste optionnelle des types de terrain par point GPX
                    Utilisé UNIQUEMENT pour affichage (tooltip + répartition).
                    N'impacte plus le calcul du temps de course.
    """
    dep_tot=float(df['dep_m'].sum())
    dp_tot =float(df['dp_cum'].max())
    dist_tot=float(df['dist_cum'].max()) if 'dist_cum' in df.columns else 0.0
    batt=100.0
    drain_s=drain_h/3600
    dep=0.0
    t=0.0
    res=[]

    if types_terrain is None or len(types_terrain) != len(df):
        types_terrain = ['sentier_large'] * len(df)

    for idx, (_, row) in enumerate(df.iterrows()):
        if row['dist_m']==0: continue
        dep+=float(row['dep_m'])
        tr=row['terrain']
        vn=profil.get(tr,{}).get('vep_norm',REF_VEP.get(tr,7.0))
        vr=vn*cat['facteur']*coeff

        # ── Fatigue mécanique : 2 composantes combinées ──
        # (a) Composante DÉNIVELÉ : la descente répétée détruit les quadriceps.
        #     Pilotée par la fraction de D+ déjà parcourue.
        rd=float(row['dp_cum'])/dp_tot if dp_tot>0 else 0
        if rd <= 0.30:
            cm_denivele = 1.0
        else:
            facteur = ((rd - 0.30) / 0.70) ** 1.5
            cm_denivele = 1.0 - 0.13 * facteur

        # (b) Composante DISTANCE/DURÉE absolue : sur une longue course même
        #     roulante (peu de D+), l'usure s'installe avec les kilomètres.
        #     Effet quasi nul jusqu'à ~25 km, puis croissant. Plafonné à -10 %.
        dist_cum_pt = float(row['dist_cum']) if 'dist_cum' in row else 0.0
        if dist_cum_pt <= 25:
            cm_distance = 1.0
        else:
            # Au-delà de 25 km, perte progressive : -10 % atteint vers ~120 km
            frac_dist = min((dist_cum_pt - 25) / 95.0, 1.0)
            cm_distance = 1.0 - 0.10 * (frac_dist ** 1.2)

        # Combinaison multiplicative (les deux fatigues se cumulent)
        cm = cm_denivele * cm_distance

        # Fatigue batterie non-linéaire
        br=batt/100
        if br >= 0.50:
            cb = 1.0
        elif br >= 0.30:
            cb = 0.92 + 0.08 * ((br - 0.30) / 0.20)
        else:
            ratio = max(0, br / 0.30)
            cb = 0.78 + 0.14 * (ratio ** 0.7)

        # Type de terrain (pour affichage uniquement, pas de coef appliqué)
        type_t = types_terrain[idx] if idx < len(types_terrain) else 'sentier_large'

        ct=cm*cb  # ← Coef total SANS la technicité
        ve=vr*ct
        vm=(ve/3.6)/float(row['cm'])
        vm=max(vm,0.3)
        ds=float(row['dist_m'])/vm
        batt=max(0.0,batt-drain_s*ds*100)
        t+=ds
        res.append({
            'dist_km':    round(float(row['dist_cum']),3),
            'altitude':   round(float(row['alt']),1),
            'dplus_cum':  round(float(row.get('dp_cum', 0)), 1),
            'dmoins_cum': round(float(row.get('dm_cum', 0)), 1),
            'terrain':    tr,
            'type_terrain': type_t,
            'effort_pct': round(dep/dep_tot*100,2) if dep_tot>0 else 0,
            'coef_meca':  round(cm,3),
            'coef_batt':  round(cb,3),
            'coef_total': round(ct,3),
            'batterie_pct':round(batt,1),
            'vitesse_kmh': round(vm*3.6,2),
            'temps_s':    round(t,1),
            'duree_s':    round(ds,3),
        })
    return res


def fourchettes(res, profil):
    tb=th=0.0
    out=[]
    for r in res:
        tr=r['terrain']
        fb=profil.get(tr,{}).get('f_basse',0.10)
        fh=profil.get(tr,{}).get('f_haute',0.10)
        ds=r['duree_s']
        tb+=ds*(1-fb); th+=ds*(1+fh)
        out.append({'dist_km':r['dist_km'],'tb':round(tb,1),'th':round(th,1)})
    return out

# ══════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════

@app.get("/")
def health():
    return {"status":"ok","app":"SUM'IT API","version":"1.0.0"}


@app.get("/api/health")
def api_health():
    """Endpoint léger (sans accès BDD) pour vérifier que le serveur est réveillé."""
    return {"status": "ok", "awake": True}


@app.post("/api/analyser-profil")
async def analyser_profil(
    fichiers:    List[UploadFile] = File(...),
    types:       str = Form(...),
    fcmax:       int = Form(193),
    profil_type: str = Form("trail"),
):
    try: types_list=json.loads(types)
    except: types_list=["entrainement"]*len(fichiers)
    if len(types_list)!=len(fichiers):
        types_list=["entrainement"]*len(fichiers)

    traces=[]
    erreurs=[]
    for i,f in enumerate(fichiers):
        try:
            data=await f.read()
            df,d0,nfc=charger_gpx(data,fcmax)
            ts=types_list[i] if i<len(types_list) else 'entrainement'
            tr=analyser_trace(df,d0,ts,fcmax)
            tr['nom']=f.filename
            tr['nb_fc']=nfc
            traces.append(tr)
        except Exception as e:
            erreurs.append({'fichier':f.filename,'erreur':str(e)})

    if not traces:
        raise HTTPException(400,detail=f"Aucune trace valide. {erreurs}")

    profil,drain=agreger(traces)
    cc=coeff_course(traces)
    arch=archetype(profil, profil_type)

    # Score d'endurance (0-100) : proxy basé sur la distance moyenne des sorties
    # et l'économie énergétique (drain faible = meilleure endurance).
    # Remplace l'ancienne valeur codée en dur (85).
    dist_moy = float(np.mean([t.get('dist_km', 0) for t in traces])) if traces else 0
    # Composante distance : 0 km → 30, 50+ km → 100 (plafonné)
    score_dist = min(100, 30 + dist_moy * 1.4)
    # Composante drain : drain bas (0.05/h) bonifie, drain haut (0.30/h) pénalise
    score_drain = max(0, 100 - (drain * 100 * 2.5)) if drain else 70
    endurance_score = int(round(0.6 * score_dist + 0.4 * score_drain))
    endurance_score = max(0, min(100, endurance_score))

    return {
        "status":"ok","nb_traces":len(traces),"traces":traces,
        "profil":profil,"drain_moy_h":drain,
        "coefficient_course":cc,"archetype":arch,
        "endurance_score":endurance_score,"erreurs":erreurs,"profil_type":profil_type,
    }


@app.post("/api/simuler")
async def api_simuler(
    fichier_cible: UploadFile = File(...),
    ravitos_km:    str   = Form(""),
    ravitos_noms:  str   = Form(""),   # JSON optionnel {"12.0": "Refuge", "25.0": "Col"}
    ravitos_pauses: str  = Form(""),   # JSON optionnel {"12.0": 5, "25.0": 10} (minutes)
    profil_json:   str   = Form(...),
    drain_moy_h:   float = Form(0.08),
    coefficient:   float = Form(1.0),
    fcmax:         int   = Form(193),
):
    # GPX cible
    try:
        data=await fichier_cible.read()
        df,_,_=charger_gpx(data,fcmax)
    except Exception as e:
        raise HTTPException(400,detail=f"Erreur GPX: {str(e)}")

    # Profil
    try:
        profil=json.loads(profil_json)
    except:
        raise HTTPException(400,detail="Profil JSON invalide")

    # Noms des ravitos (mapping km → nom)
    noms_ravitos = {}
    if ravitos_noms.strip():
        try:
            raw = json.loads(ravitos_noms)
            # Clés en float arrondi pour le matching
            noms_ravitos = {round(float(k), 1): str(v) for k, v in raw.items()}
        except Exception:
            noms_ravitos = {}

    # Pauses aux ravitos (mapping km → minutes d'arrêt)
    pauses_ravitos = {}
    if ravitos_pauses.strip():
        try:
            raw = json.loads(ravitos_pauses)
            pauses_ravitos = {round(float(k), 1): max(0.0, float(v)) for k, v in raw.items()}
        except Exception:
            pauses_ravitos = {}

    dist_km=float(df['dist_cum'].max())
    dplus_m=float(df['dp_cum'].max())
    dmoins_m=float(df['dm_cum'].max()) if 'dm_cum' in df.columns else dplus_m
    dep_km =float(df['dep_cum'].max())
    cat=categorie(dist_km)

    # Ravitos
    ravs=[]
    if ravitos_km.strip():
        for r in ravitos_km.split(','):
            try:
                km=float(r.strip())
                if 0<km<dist_km: ravs.append(km)
            except: pass
    if not ravs:
        ravs=[round(dist_km*p,1) for p in [0.2,0.4,0.6,0.8]]

    # ── Classification du terrain via OpenStreetMap (info uniquement) ──
    # Si OSM ne répond pas, on continue avec un terrain neutre.
    # L'OSM n'impacte pas le calcul, juste l'affichage.
    types_terrain = ['sentier_large'] * len(df)
    try:
        types_terrain = classifier_trace_via_osm(df)
        print(f"✅ OSM : {len(set(types_terrain))} types détectés")
    except Exception as e:
        print(f"⚠️ OSM indisponible (utilisation terrain neutre) : {e}")

    # Simulation (technicité affichée mais sans impact sur le temps)
    res=simuler(df,profil,drain_moy_h,cat,coefficient,types_terrain)
    fch=fourchettes(res,profil)
    if not res:
        raise HTTPException(500,detail="Simulation vide")

    tt=res[-1]['temps_s']
    tb=fch[-1]['tb']
    th=fch[-1]['th']
    bf=res[-1]['batterie_pct']
    am=round((tt/60)/dist_km,1) if dist_km>0 else 0

    sdf=pd.DataFrame(res)
    fdf=pd.DataFrame(fch)

    # Ravitos data
    rvd=[]
    ravs_tries = sorted(ravs)  # ordre kilométrique pour cumuler les pauses
    pause_cumulee_s = 0.0       # somme des pauses des ravitos déjà passés
    for km in ravs_tries:
        idx=int((sdf['dist_km']-km).abs().idxmin())
        t_ =float(sdf.loc[idx,'temps_s'])
        tb_=float(fdf.loc[idx,'tb'])
        th_=float(fdf.loc[idx,'th'])
        b_ =float(sdf.loc[idx,'batterie_pct'])
        dp_=float(sdf.loc[idx,'dplus_cum']) if 'dplus_cum' in sdf.columns else 0
        dm_=float(sdf.loc[idx,'dmoins_cum']) if 'dmoins_cum' in sdf.columns else 0
        nom_rv = noms_ravitos.get(round(km, 1), '')

        # Pause à ce ravito (minutes → secondes)
        pause_min = pauses_ravitos.get(round(km, 1), 0.0)
        pause_s = pause_min * 60.0
        # Le temps de passage inclut les pauses des ravitos précédents + celle-ci
        # (on considère que le coureur s'arrête en arrivant au ravito)
        pause_cumulee_s += pause_s
        t_avec_pauses  = t_  + pause_cumulee_s
        tb_avec_pauses = tb_ + pause_cumulee_s
        th_avec_pauses = th_ + pause_cumulee_s

        rvd.append({
            'km':round(km,1),
            'nom':nom_rv,
            'pause_min':round(pause_min,0),
            'temps_s':round(t_avec_pauses,1),'temps_bas_s':round(tb_avec_pauses,1),'temps_haut_s':round(th_avec_pauses,1),
            'batterie_pct':round(b_,1),
            'dplus_cum':round(dp_,0),
            'dmoins_cum':round(dm_,0),
            'temps_fmt':fmt(t_avec_pauses),'bas_fmt':fmt(tb_avec_pauses),'haut_fmt':fmt(th_avec_pauses),
        })

    # Temps total de pause (toutes les pauses, à ajouter au temps d'arrivée)
    pause_totale_s = sum(v * 60.0 for v in pauses_ravitos.values())

    # Répartition terrain
    rep={}
    for t in ORDRE_TERRAINS:
        sub=sdf[sdf['terrain']==t]
        if len(sub)==0: continue
        ts_=float(sub['duree_s'].sum())
        rep[t]={'temps_s':round(ts_,1),'pct':round(ts_/tt*100,1) if tt>0 else 0,'temps_fmt':fmt(ts_)}

    # Graphique
    n=min(150,len(sdf))
    step=max(1,len(sdf)//n)
    chart=sdf.iloc[::step][['dist_km','altitude','terrain','type_terrain','vitesse_kmh','batterie_pct']].round(2).to_dict('records')

    # Répartition par type de terrain (technicité)
    rep_terrain_type = {}
    for tt_name in ORDRE_TERRAIN_TYPES:
        sub_tt = sdf[sdf['type_terrain'] == tt_name]
        if len(sub_tt) == 0:
            continue
        dist_tt = float(sub_tt['dist_km'].max() - sub_tt['dist_km'].min()) if len(sub_tt) > 1 else 0
        # On compte plutôt en nombre de points pour avoir la part du parcours
        pct = round(len(sub_tt) / len(sdf) * 100, 1)
        rep_terrain_type[tt_name] = {
            'nom': TERRAIN_TYPES[tt_name]['nom'],
            'emoji': TERRAIN_TYPES[tt_name]['emoji'],
            'pct': pct,
            'coef_vitesse': TERRAIN_TYPES[tt_name]['coef_vitesse'],
        }

    return {
        "status":"ok",
        "distance_km":round(dist_km,2),
        "dplus_m":round(dplus_m,0),
        "dmoins_m":round(dmoins_m,0),
        "dep_km":round(dep_km,2),
        "categorie":{
            "nom":cat["nom"],
            "emoji":cat["emoji"],
            "facteur":cat["facteur"],
        },
        "temps_total_s":round(tt + pause_totale_s, 1),
        "temps_bas_s":round(tb + pause_totale_s, 1),
        "temps_haut_s":round(th + pause_totale_s, 1),
        "temps_fmt":fmt(tt + pause_totale_s),
        "bas_fmt":fmt(tb + pause_totale_s),
        "haut_fmt":fmt(th + pause_totale_s),
        "pause_totale_s":round(pause_totale_s, 0),
        "pause_totale_fmt":fmt(pause_totale_s) if pause_totale_s > 0 else None,
        "allure_moy":am,
        "batt_finale":round(bf,1),
        "coefficient_course":round(coefficient,3),
        "ravitos":rvd,
        "repartition":rep,
        "profil_chart":chart,
        "repartition_terrain_type": rep_terrain_type,
    }


# ══════════════════════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  ROUTES AUTHENTIFICATION GOOGLE
# ══════════════════════════════════════════════════════════════

@app.get("/api/auth/google/login")
def auth_google_login():
    """Redirige vers Google pour démarrer le flow OAuth."""
    return RedirectResponse(url=construire_url_google_auth())


@app.get("/api/auth/google/callback")
async def auth_google_callback(code: str, db: Session = Depends(get_db)):
    """Callback après authentification Google. Crée/met à jour le user et redirige vers le frontend avec le JWT."""
    try:
        google_user = await echanger_code_google(code)
        user = upsert_user_google(db, google_user)
        token = creer_jwt(user.id, user.email)
        # Redirige vers le frontend avec le token en paramètre
        return RedirectResponse(url=f"{FRONTEND_URL}/?token={token}")
    except HTTPException:
        raise
    except Exception as e:
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth_error={urllib.parse.quote(str(e))}")


@app.get("/api/me")
def api_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retourne les infos de l'utilisateur connecté + ses profils."""
    profiles = db.query(Profile).filter(Profile.user_id == user.id).all()
    return {
        "id":      user.id,
        "email":   user.email,
        "name":    user.name,
        "picture": user.picture,
        "prenom":  user.prenom,
        "fcmax":   user.fcmax,
        "strava_connected": bool(user.strava_athlete_id),
        "profiles": [
            {
                "id":   p.id,
                "type": p.type,
                "vep_globale": p.vep_globale,
                "coefficient_course": p.coefficient_course,
                "drain_moy_h": p.drain_moy_h,
                "nb_traces":   p.nb_traces,
                "updated_at":  p.updated_at.isoformat() if p.updated_at else None,
                "archetype":   p.archetype,
                "profil_data": p.profil_data,
            }
            for p in profiles
        ],
    }


@app.post("/api/me/settings")
def update_user_settings(
    prenom: Optional[str] = Form(None),
    fcmax:  Optional[int] = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour les paramètres utilisateur (prénom, FCmax)."""
    if prenom is not None:
        user.prenom = prenom
    if fcmax is not None:
        user.fcmax = fcmax
    db.commit()
    return {"status": "ok", "prenom": user.prenom, "fcmax": user.fcmax}


# ══════════════════════════════════════════════════════════════
#  ROUTES PROFILS (Trail/Rando) - persistence
# ══════════════════════════════════════════════════════════════

@app.post("/api/profil/save")
def save_profile(
    profil_type: str = Form(...),  # 'trail' ou 'rando'
    profil_json: str = Form(...),
    archetype_json: str = Form(...),
    drain_moy_h: float = Form(...),
    coefficient_course: float = Form(...),
    vep_globale: float = Form(...),
    nb_traces: int = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sauvegarde ou met à jour le profil (trail ou rando) de l'utilisateur."""
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")

    try:
        profil_data = json.loads(profil_json)
        archetype   = json.loads(archetype_json)
    except Exception as e:
        raise HTTPException(400, detail=f"JSON invalide: {e}")

    # Cherche s'il existe déjà
    profile = db.query(Profile).filter(
        Profile.user_id == user.id,
        Profile.type == profil_type
    ).first()

    if profile:
        profile.profil_data = profil_data
        profile.archetype   = archetype
        profile.drain_moy_h = drain_moy_h
        profile.coefficient_course = coefficient_course
        profile.vep_globale = vep_globale
        profile.nb_traces   = nb_traces
    else:
        profile = Profile(
            user_id      = user.id,
            type         = profil_type,
            profil_data  = profil_data,
            archetype    = archetype,
            drain_moy_h  = drain_moy_h,
            coefficient_course = coefficient_course,
            vep_globale  = vep_globale,
            nb_traces    = nb_traces,
        )
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return {"status": "ok", "profile_id": profile.id, "type": profile.type}


@app.get("/api/profil/{profil_type}")
def get_profile(
    profil_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupère le profil trail ou rando de l'utilisateur."""
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")

    profile = db.query(Profile).filter(
        Profile.user_id == user.id,
        Profile.type == profil_type
    ).first()

    if not profile:
        raise HTTPException(404, detail="Aucun profil enregistré")

    return {
        "profil":      profile.profil_data,
        "archetype":   profile.archetype,
        "drain_moy_h": profile.drain_moy_h,
        "coefficient": profile.coefficient_course,
        "vep_globale": profile.vep_globale,
        "nb_traces":   profile.nb_traces,
        "fcmax":       user.fcmax,
        "prenom":      user.prenom,
        "type":        profile.type,
        "updated_at":  profile.updated_at.isoformat() if profile.updated_at else None,
    }


# ══════════════════════════════════════════════════════════════
#  ROUTES STRAVA
# ══════════════════════════════════════════════════════════════

@app.get("/api/strava/login")
def strava_login(token: str):
    """
    Démarre la connexion Strava.
    Le token JWT est passé en query param pour identifier le user au callback.
    """
    return RedirectResponse(url=construire_url_strava_auth(state=token))


@app.get("/api/strava/callback")
async def strava_callback(
    code: str,
    state: str,  # JWT du user
    db: Session = Depends(get_db),
):
    """Callback Strava : sauvegarde les tokens dans le user."""
    from auth import decoder_jwt
    try:
        payload = decoder_jwt(state)
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        if not user:
            raise HTTPException(401, detail="Utilisateur introuvable")

        token_data = await echanger_code_strava(code)
        sauvegarder_tokens_strava(db, user, token_data)

        return RedirectResponse(url=f"{FRONTEND_URL}/pages/profil.html?strava_connected=1")
    except Exception as e:
        return RedirectResponse(url=f"{FRONTEND_URL}/pages/profil.html?strava_error={urllib.parse.quote(str(e))}")


@app.get("/api/strava/activities")
async def strava_activities(
    per_page: int = 30,
    page: int = 1,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste les activités Strava du user."""
    if not user.strava_athlete_id:
        raise HTTPException(401, detail="Compte Strava non connecté")

    activities = await lister_activites_strava(db, user, per_page=per_page, page=page)
    return {"activities": activities}


@app.post("/api/strava/import/{activity_id}")
async def strava_import_activity(
    activity_id: str,
    type_sortie: str = Form("entrainement"),  # course/entrainement/sortie
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Télécharge une activité Strava sous forme de GPX exploitable.
    Retourne le GPX en base64 pour que le frontend l'utilise comme un fichier importé.
    """
    if not user.strava_athlete_id:
        raise HTTPException(401, detail="Compte Strava non connecté")

    try:
        gpx_bytes = await telecharger_gpx_strava(db, user, activity_id)
        import base64
        return {
            "status": "ok",
            "gpx_base64": base64.b64encode(gpx_bytes).decode("utf-8"),
            "type_sortie": type_sortie,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"Erreur import: {e}")


@app.post("/api/strava/disconnect")
def strava_disconnect(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Déconnecte Strava (efface les tokens)."""
    user.strava_athlete_id = None
    user.strava_access_token = None
    user.strava_refresh_token = None
    user.strava_token_expires = None
    db.commit()
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════
#  ROUTES ACTIVITÉS (traces stockées par utilisateur)
# ══════════════════════════════════════════════════════════════

def _recalculer_profil_user(db: Session, user: User, profil_type: str, activity_id: int = None):
    """
    Recalcule le profil agrégé d'un utilisateur à partir de toutes ses
    activités sauvegardées en BDD. Sauvegarde le résultat dans Profile.

    Exclut les simulations épinglées (source='simulation') qui ne sont
    pas de vraies traces GPX d'entraînement.

    Si activity_id est fourni → crée un snapshot lié à cette activité.
    Sinon → ne crée pas de snapshot (c'est juste un recalcul après suppression).
    """
    activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.type_profil == profil_type,
        Activity.source != 'simulation',  # ← exclut les sims
    ).all()

    if not activities:
        # Pas d'activité → supprime le profil + tous les snapshots
        existing = db.query(Profile).filter(
            Profile.user_id == user.id,
            Profile.type == profil_type
        ).first()
        if existing:
            db.delete(existing)
        db.query(ProfilSnapshot).filter(
            ProfilSnapshot.user_id == user.id,
            ProfilSnapshot.type_profil == profil_type,
        ).delete()
        db.commit()
        return None

    # Reconstruction de la liste "traces" attendue par agreger() et coeff_course()
    traces = []
    for a in activities:
        td = a.trace_data or {}
        # Chaque activité contient son analyse pré-calculée
        traces.append(td)

    if not traces:
        return None

    try:
        profil, drain = agreger(traces)
        cc = coeff_course(traces)
        arch = archetype(profil, profil_type)
    except Exception as e:
        print(f"⚠️ Échec recalcul profil : {e}")
        return None

    # VEP globale moyenne pondérée
    vep_glob = sum(t.get('vep_globale', 0) for t in traces) / len(traces) if traces else 0

    # Upsert dans Profile
    existing = db.query(Profile).filter(
        Profile.user_id == user.id,
        Profile.type == profil_type
    ).first()

    if existing:
        existing.profil_data        = profil
        existing.archetype          = arch
        existing.coefficient_course = cc.get('coefficient', 1.0)
        existing.drain_moy_h        = drain
        existing.vep_globale        = vep_glob
        existing.nb_traces          = len(traces)
    else:
        existing = Profile(
            user_id=user.id, type=profil_type,
            profil_data=profil, archetype=arch,
            coefficient_course=cc.get('coefficient', 1.0),
            drain_moy_h=drain, vep_globale=vep_glob,
            nb_traces=len(traces),
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    # Snapshot uniquement si activity_id est fourni (= un ajout d'activité)
    if activity_id is not None:
        try:
            _creer_snapshot(db, user, profil_type, profil, arch, drain, cc, vep_glob, traces, activities, activity_id)
        except Exception as e:
            print(f"⚠️ Échec création snapshot : {e}")

    return existing


def _creer_snapshot(db, user, profil_type, profil, arch, drain, cc, vep_glob, traces, activities, activity_id):
    """Crée un snapshot du profil lié à une activité spécifique."""
    # Calculer scores montée / descente
    score_montee = 0.0
    score_descente = 0.0
    montees = ['montee_raide', 'montee_soutenue', 'montee_douce']
    descentes = ['descente_douce', 'descente_soutenue', 'descente_raide']

    nb_m, nb_d = 0, 0
    for t in montees:
        if t in profil and 'ecart_plat_pct' in profil[t]:
            score_montee += profil[t]['ecart_plat_pct']
            nb_m += 1
    for t in descentes:
        if t in profil and 'ecart_plat_pct' in profil[t]:
            score_descente += profil[t]['ecart_plat_pct']
            nb_d += 1

    if nb_m > 0: score_montee /= nb_m
    if nb_d > 0: score_descente /= nb_d

    # Distance moyenne
    dist_moy = sum(t.get('dist_km', 0) for t in traces) / len(traces) if traces else 0.0

    # Date de l'activité qui déclenche le snapshot (= date de la course)
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    date_act = act.date_activity if act else None

    # Normaliser le nom d'archétype (retirer "Le ", "La ", "L'" pour matcher les couleurs)
    arch_nom_brut = (arch or {}).get('nom', None) or ''
    arch_nom = arch_nom_brut.replace("L'", "").replace("Le ", "").replace("La ", "").strip()

    snap = ProfilSnapshot(
        user_id            = user.id,
        type_profil        = profil_type,
        activity_id        = activity_id,
        date_activity      = date_act,
        vep_globale        = vep_glob,
        drain_moy_h        = drain,
        coefficient_course = cc.get('coefficient', 1.0),
        nb_traces          = len(traces),
        dist_moy_km        = dist_moy,
        score_montee       = score_montee,
        score_descente     = score_descente,
        archetype_nom      = arch_nom,
    )
    db.add(snap)
    db.commit()


@app.get("/api/evolution")
def get_evolution(
    profil_type: str = "trail",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retourne l'historique des snapshots pour tracer l'évolution du coureur.
    Tri chronologique (par date d'activité la plus récente à chaque snapshot).
    """
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")

    snaps = db.query(ProfilSnapshot).filter(
        ProfilSnapshot.user_id == user.id,
        ProfilSnapshot.type_profil == profil_type,
    ).order_by(ProfilSnapshot.created_at.asc()).all()

    return {
        "snapshots": [
            {
                "id":                 s.id,
                "created_at":         s.created_at.isoformat() if s.created_at else None,
                "date_activity":      s.date_activity.isoformat() if s.date_activity else None,
                "vep_globale":        round(s.vep_globale, 2),
                "drain_moy_h":        round(s.drain_moy_h, 4),
                "coefficient_course": round(s.coefficient_course, 3),
                "nb_traces":          s.nb_traces,
                "dist_moy_km":        round(s.dist_moy_km, 1),
                "score_montee":       round(s.score_montee, 2),
                "score_descente":     round(s.score_descente, 2),
                "archetype_nom":      s.archetype_nom,
            }
            for s in snaps
        ]
    }


@app.get("/api/activities")
def list_activities(
    profil_type: str = "trail",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste les activités de l'utilisateur pour un profil donné (hors simulations épinglées)."""
    activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.type_profil == profil_type,
        Activity.source != 'simulation',  # ← exclut les sims épinglées
    ).order_by(Activity.date_activity.desc().nullslast()).all()

    return {
        "activities": [
            {
                "id":          a.id,
                "source":      a.source,
                "external_id": a.external_id,
                "name":        a.name,
                "type_sortie": a.type_sortie,
                "type_profil": a.type_profil,
                "date":        a.date_activity.isoformat() if a.date_activity else None,
                "dist_km":     a.dist_km,
                "dplus_m":     a.dplus_m,
                "duree_s":     a.duree_s,
                "vep_globale": a.vep_globale,
            }
            for a in activities
        ]
    }


@app.post("/api/activities/add")
async def add_activity_gpx(
    fichier:     UploadFile = File(...),
    type_sortie: str = Form("entrainement"),
    profil_type: str = Form("trail"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ajoute une activité GPX (import classique) et recalcule le profil."""
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")

    try:
        data = await fichier.read()
        df, d0, nfc = charger_gpx(data, user.fcmax)
        tr = analyser_trace(df, d0, type_sortie, user.fcmax)
        # Enrichissement : trackpoints + alt min/max pour visualisation
        tr['_trackpoints'] = extraire_trackpoints(df, max_points=200)
        if 'alt' in df.columns:
            tr['alt_min'] = round(float(df['alt'].min()), 1)
            tr['alt_max'] = round(float(df['alt'].max()), 1)
        if 'dm_cum' in df.columns:
            tr['dmoins_m'] = round(float(df['dm_cum'].max()), 0)
        if 'vitesse_kmh' in df.columns and df['duree_s'].sum() > 0:
            tr['allure_moy_kmh'] = round(float((df['dist_m'].sum() / 1000) / (df['duree_s'].sum() / 3600)), 2)
    except Exception as e:
        raise HTTPException(400, detail=f"GPX invalide : {e}")

    # Stockage en BDD
    activity = Activity(
        user_id      = user.id,
        source       = 'manual',
        name         = fichier.filename,
        type_sortie  = type_sortie,
        type_profil  = profil_type,
        date_activity= d0,
        dist_km      = tr.get('dist_km', 0),
        dplus_m      = tr.get('dplus_m', 0),
        duree_s      = int(tr.get('duree_h', 0) * 3600),
        vep_globale  = tr.get('vep_globale', 0),
        trace_data   = tr,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    # Recalcul du profil + snapshot lié à cette activité
    _recalculer_profil_user(db, user, profil_type, activity_id=activity.id)

    return {"status": "ok", "activity_id": activity.id}


@app.post("/api/activities/add-strava")
async def add_activity_strava(
    strava_id:   str = Form(...),
    type_sortie: str = Form("entrainement"),
    profil_type: str = Form("trail"),
    nom:         str = Form(""),  # Nom de l'activité (sinon récupéré depuis Strava)
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Importe une activité Strava et l'ajoute au profil."""
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")
    if not user.strava_athlete_id:
        raise HTTPException(401, detail="Compte Strava non connecté")

    # Vérifier si déjà importée
    existing = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.source == 'strava',
        Activity.external_id == strava_id,
    ).first()
    if existing:
        raise HTTPException(400, detail="Cette activité Strava est déjà importée")

    # Télécharger le GPX depuis Strava (et récupérer le nom si pas fourni)
    try:
        gpx_bytes = await telecharger_gpx_strava(db, user, strava_id)
        df, d0, nfc = charger_gpx(gpx_bytes, user.fcmax)
        tr = analyser_trace(df, d0, type_sortie, user.fcmax)
        tr['_trackpoints'] = extraire_trackpoints(df, max_points=200)
        if 'alt' in df.columns:
            tr['alt_min'] = round(float(df['alt'].min()), 1)
            tr['alt_max'] = round(float(df['alt'].max()), 1)
        if 'dm_cum' in df.columns:
            tr['dmoins_m'] = round(float(df['dm_cum'].max()), 0)
        if 'vitesse_kmh' in df.columns and df['duree_s'].sum() > 0:
            tr['allure_moy_kmh'] = round(float((df['dist_m'].sum() / 1000) / (df['duree_s'].sum() / 3600)), 2)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, detail=f"Erreur import Strava : {e}")

    # Nom final : celui fourni en argument > celui de l'activité Strava > fallback
    nom_final = (nom or '').strip()
    if not nom_final:
        # Récupérer le nom depuis l'activité Strava
        try:
            from strava import rafraichir_token_strava, STRAVA_API_BASE
            import httpx as _httpx
            access_token = await rafraichir_token_strava(db, user)
            async with _httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{STRAVA_API_BASE}/activities/{strava_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if r.status_code == 200:
                    nom_final = (r.json() or {}).get('name', '') or ''
        except Exception:
            pass
    if not nom_final:
        nom_final = f"Activité Strava du {d0.strftime('%d/%m/%Y') if d0 else '?'}"

    activity = Activity(
        user_id      = user.id,
        source       = 'strava',
        external_id  = strava_id,
        name         = nom_final,
        type_sortie  = type_sortie,
        type_profil  = profil_type,
        date_activity= d0,
        dist_km      = tr.get('dist_km', 0),
        dplus_m      = tr.get('dplus_m', 0),
        duree_s      = int(tr.get('duree_h', 0) * 3600),
        vep_globale  = tr.get('vep_globale', 0),
        trace_data   = tr,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    _recalculer_profil_user(db, user, profil_type, activity_id=activity.id)

    return {"status": "ok", "activity_id": activity.id}


@app.delete("/api/activities/{activity_id}")
def delete_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime une activité et recalcule le profil."""
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user.id
    ).first()

    if not activity:
        raise HTTPException(404, detail="Activité introuvable")

    profil_type = activity.type_profil

    # Supprimer le snapshot lié à cette activité
    db.query(ProfilSnapshot).filter(
        ProfilSnapshot.user_id == user.id,
        ProfilSnapshot.activity_id == activity_id,
    ).delete()

    db.delete(activity)
    db.commit()

    _recalculer_profil_user(db, user, profil_type)

    return {"status": "ok"}


@app.post("/api/profil/recalculer")
def recalculer_profil(
    profil_type: str = Form("trail"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Force le recalcul complet du profil (toutes les activités) pour un type donné.
    Utile après une mise à jour de l'algorithme : applique les corrections aux
    profils existants sans avoir à réimporter les activités.
    """
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")
    _recalculer_profil_user(db, user, profil_type)
    return {"status": "ok", "profil_type": profil_type}


@app.post("/api/evolution/rebuild")
def rebuild_evolution(
    profil_type: str = "trail",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reconstruit proprement l'historique d'évolution :
    1. Supprime tous les snapshots existants du profil
    2. Trie les activités par date d'activité (date de la course)
    3. Pour chaque activité, calcule le profil cumulé et crée un snapshot
    Résultat : une courbe d'évolution chronologiquement cohérente.
       - Premier snapshot = première course (chronologiquement) seule
       - Dernier snapshot = moyenne de toutes les activités
    """
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")

    # 1. Suppression des snapshots existants
    db.query(ProfilSnapshot).filter(
        ProfilSnapshot.user_id == user.id,
        ProfilSnapshot.type_profil == profil_type,
    ).delete()
    db.commit()

    # 2. Récup activités triées par date_activity ASC (date de la course)
    # Avec fallback sur created_at pour les activités sans date
    activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.type_profil == profil_type,
        Activity.source != 'simulation',
    ).order_by(Activity.date_activity.asc().nullslast(), Activity.created_at.asc()).all()

    if not activities:
        return {"status": "ok", "snapshots_crees": 0}

    montees   = ['montee_raide', 'montee_soutenue', 'montee_douce']
    descentes = ['descente_douce', 'descente_soutenue', 'descente_raide']

    # 3. Reconstruction snapshot par snapshot (cumulatif chronologique)
    nb = 0
    for i, act in enumerate(activities):
        traces_cumul = []
        for j in range(i + 1):
            td = activities[j].trace_data or {}
            if td:
                traces_cumul.append(td)

        if not traces_cumul:
            continue

        try:
            profil, drain = agreger(traces_cumul)
            cc = coeff_course(traces_cumul)
            arch = archetype(profil, profil_type)

            vep_glob = sum(t.get('vep_globale', 0) for t in traces_cumul) / len(traces_cumul)
            dist_moy = sum(t.get('dist_km', 0) for t in traces_cumul) / len(traces_cumul)

            # Scores montée / descente
            score_montee = 0.0
            score_descente = 0.0
            nb_m, nb_d = 0, 0
            for t in montees:
                if t in profil and 'ecart_plat_pct' in profil[t]:
                    score_montee += profil[t]['ecart_plat_pct']
                    nb_m += 1
            for t in descentes:
                if t in profil and 'ecart_plat_pct' in profil[t]:
                    score_descente += profil[t]['ecart_plat_pct']
                    nb_d += 1
            if nb_m > 0: score_montee /= nb_m
            if nb_d > 0: score_descente /= nb_d

            # Normaliser le nom d'archétype
            arch_nom_brut = (arch or {}).get('nom', None) or ''
            arch_nom = arch_nom_brut.replace("L'", "").replace("Le ", "").replace("La ", "").strip()

            snap = ProfilSnapshot(
                user_id            = user.id,
                type_profil        = profil_type,
                activity_id        = act.id,
                date_activity      = act.date_activity,
                vep_globale        = vep_glob,
                drain_moy_h        = drain,
                coefficient_course = cc.get('coefficient', 1.0),
                nb_traces          = len(traces_cumul),
                dist_moy_km        = dist_moy,
                score_montee       = score_montee,
                score_descente     = score_descente,
                archetype_nom      = arch_nom,
            )
            db.add(snap)
            nb += 1
        except Exception as e:
            print(f"⚠️ Erreur rebuild snapshot pour activité {act.id} : {e}")

    db.commit()
    return {"status": "ok", "snapshots_crees": nb}


@app.get("/api/activities/{activity_id}")
def get_activity_detail(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Détail complet d'une activité : trackpoints + KPIs."""
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user.id
    ).first()

    if not activity:
        raise HTTPException(404, detail="Activité introuvable")

    td = activity.trace_data or {}
    trackpoints = td.get('_trackpoints', [])

    # Allure moyenne en km/h (fallback)
    allure_moy = td.get('allure_moy_kmh', 0)
    if not allure_moy and activity.duree_s > 0 and activity.dist_km > 0:
        allure_moy = round(activity.dist_km / (activity.duree_s / 3600), 2)

    return {
        "id":            activity.id,
        "name":          activity.name,
        "source":        activity.source,
        "type_sortie":   activity.type_sortie,
        "type_profil":   activity.type_profil,
        "date":          activity.date_activity.isoformat() if activity.date_activity else None,
        "dist_km":       activity.dist_km,
        "dplus_m":       activity.dplus_m,
        "dmoins_m":      td.get('dmoins_m', activity.dplus_m),
        "duree_s":       activity.duree_s,
        "vep_globale":   activity.vep_globale,
        "allure_moy_kmh": allure_moy,
        "alt_min":       td.get('alt_min', 0),
        "alt_max":       td.get('alt_max', 0),
        "trackpoints":   trackpoints,
    }


@app.patch("/api/activities/{activity_id}")
def update_activity(
    activity_id: int,
    name: Optional[str] = Form(None),
    type_sortie: Optional[str] = Form(None),
    date_activity: Optional[str] = Form(None),  # format ISO 'YYYY-MM-DD' ou ISO complet
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour le nom, le type et/ou la date d'une activité.
    Recalcule le profil et les snapshots si le type ou la date change."""
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user.id
    ).first()

    if not activity:
        raise HTTPException(404, detail="Activité introuvable")

    type_change = False
    date_change = False

    if name is not None:
        activity.name = name.strip()[:200] or activity.name

    if type_sortie is not None and type_sortie in ('course', 'entrainement', 'sortie', 'resultat', 'rando'):
        if activity.type_sortie != type_sortie:
            activity.type_sortie = type_sortie
            type_change = True
            # Mettre à jour aussi type_sortie dans le trace_data pour le recalcul
            if activity.trace_data:
                td = dict(activity.trace_data)
                td['type_sortie'] = type_sortie
                POIDS_TYPE_LOC = {'course': 1.0, 'resultat': 1.0, 'rando': 1.0, 'entrainement': 0.7, 'sortie': 0.4}
                td['poids_type'] = POIDS_TYPE_LOC.get(type_sortie, 0.7)
                td['poids_total'] = round(td.get('poids_temporel', 0.5) * td['poids_type'], 3)
                activity.trace_data = td

    if date_activity is not None and date_activity.strip():
        try:
            # Accepte 'YYYY-MM-DD' (input HTML date) ou ISO complet
            s = date_activity.strip()
            if len(s) == 10:  # YYYY-MM-DD
                from datetime import datetime as _dt
                new_date = _dt.strptime(s, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            else:
                new_date = datetime.fromisoformat(s.replace('Z', '+00:00'))
            if activity.date_activity != new_date:
                activity.date_activity = new_date
                date_change = True
        except Exception as e:
            raise HTTPException(400, detail=f"Date invalide : {e}")

    db.commit()
    db.refresh(activity)

    # Si le type ou la date a changé → recalcul du profil + rebuild des snapshots
    # (la date affecte l'ordre chronologique de l'évolution)
    if type_change or date_change:
        _recalculer_profil_user(db, user, activity.type_profil)
        # Rebuild complet de l'évolution si la date a changé
        if date_change:
            try:
                # Suppression snapshots + reconstruction chronologique
                db.query(ProfilSnapshot).filter(
                    ProfilSnapshot.user_id == user.id,
                    ProfilSnapshot.type_profil == activity.type_profil,
                ).delete()
                db.commit()
                # Reconstruction via la même logique que /api/evolution/rebuild
                acts = db.query(Activity).filter(
                    Activity.user_id == user.id,
                    Activity.type_profil == activity.type_profil,
                    Activity.source != 'simulation',
                ).order_by(Activity.date_activity.asc().nullslast(), Activity.created_at.asc()).all()
                montees = ['montee_raide', 'montee_soutenue', 'montee_douce']
                descentes = ['descente_douce', 'descente_soutenue', 'descente_raide']
                for i, act in enumerate(acts):
                    traces_cumul = [a.trace_data for a in acts[:i+1] if a.trace_data]
                    if not traces_cumul: continue
                    try:
                        profil, drain = agreger(traces_cumul)
                        cc = coeff_course(traces_cumul)
                        arch = archetype(profil, activity.type_profil)
                        vep_glob = sum(t.get('vep_globale', 0) for t in traces_cumul) / len(traces_cumul)
                        dist_moy = sum(t.get('dist_km', 0) for t in traces_cumul) / len(traces_cumul)
                        sm, sd, nm, nd = 0.0, 0.0, 0, 0
                        for t in montees:
                            if t in profil and 'ecart_plat_pct' in profil[t]:
                                sm += profil[t]['ecart_plat_pct']; nm += 1
                        for t in descentes:
                            if t in profil and 'ecart_plat_pct' in profil[t]:
                                sd += profil[t]['ecart_plat_pct']; nd += 1
                        if nm > 0: sm /= nm
                        if nd > 0: sd /= nd
                        arch_nom_brut = (arch or {}).get('nom', '') or ''
                        arch_nom = arch_nom_brut.replace("L'", "").replace("Le ", "").replace("La ", "").strip()
                        snap = ProfilSnapshot(
                            user_id=user.id, type_profil=activity.type_profil,
                            activity_id=act.id, date_activity=act.date_activity,
                            vep_globale=vep_glob, drain_moy_h=drain,
                            coefficient_course=cc.get('coefficient', 1.0),
                            nb_traces=len(traces_cumul), dist_moy_km=dist_moy,
                            score_montee=sm, score_descente=sd, archetype_nom=arch_nom,
                        )
                        db.add(snap)
                    except Exception as e:
                        print(f"⚠️ Snapshot {act.id}: {e}")
                db.commit()
            except Exception as e:
                print(f"⚠️ Rebuild après changement date : {e}")

    return {
        "status": "ok",
        "id": activity.id,
        "name": activity.name,
        "type_sortie": activity.type_sortie,
    }


# ══════════════════════════════════════════════════════════════
#  ROUTES SIMULATIONS ÉPINGLÉES
# ══════════════════════════════════════════════════════════════

# On stocke les simulations épinglées dans la table Activity avec source='simulation'
# C'est un hack léger pour éviter une nouvelle table.

@app.get("/api/simulations")
def list_simulations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste les simulations épinglées."""
    sims = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).order_by(Activity.created_at.desc()).all()

    return {
        "simulations": [
            {
                "id":          s.id,
                "name":        s.name,
                "type_profil": s.type_profil,
                "created_at":  s.created_at.isoformat() if s.created_at else None,
                "dist_km":     s.dist_km,
                "dplus_m":     s.dplus_m,
                "duree_s":     s.duree_s,
                "sim_data":    s.trace_data,
            }
            for s in sims
        ]
    }


@app.post("/api/simulations/pin")
def pin_simulation(
    nom_course:  str = Form(...),
    profil_type: str = Form(...),
    sim_data:    str = Form(...),
    gpx_base64:  str = Form(""),  # GPX original encodé en base64 (optionnel)
    ravitos_km:  str = Form(""),  # Liste des ravitos pour recalcul
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Épingle une simulation avec son GPX pour pouvoir la rouvrir/recalculer."""
    # Limite à 20 par user
    count = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).count()

    if count >= 20:
        raise HTTPException(400, detail="Limite de 20 simulations épinglées atteinte. Supprime-en avant d'en ajouter.")

    try:
        sim = json.loads(sim_data)
    except Exception as e:
        raise HTTPException(400, detail=f"sim_data invalide : {e}")

    # On stocke le GPX + ravitos + résultats dans trace_data
    trace_data = {
        **sim,
        '_gpx_base64': gpx_base64 or None,
        '_ravitos_km': ravitos_km or None,
    }

    activity = Activity(
        user_id      = user.id,
        source       = 'simulation',
        name         = nom_course,
        type_profil  = profil_type,
        type_sortie  = 'course',
        date_activity= datetime.now(timezone.utc),
        dist_km      = sim.get('distance_km', 0),
        dplus_m      = sim.get('dplus_m', 0),
        duree_s      = sim.get('temps_total_s', 0),
        vep_globale  = 0,
        trace_data   = trace_data,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {"status": "ok", "simulation_id": activity.id}


@app.get("/api/simulations/{simulation_id}")
def get_simulation(
    simulation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupère le détail complet d'une simulation épinglée (avec GPX si présent)."""
    sim = db.query(Activity).filter(
        Activity.id == simulation_id,
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).first()

    if not sim:
        raise HTTPException(404, detail="Simulation introuvable")

    td = sim.trace_data or {}
    return {
        "id":          sim.id,
        "name":        sim.name,
        "type_profil": sim.type_profil,
        "created_at":  sim.created_at.isoformat() if sim.created_at else None,
        "dist_km":     sim.dist_km,
        "dplus_m":     sim.dplus_m,
        "duree_s":     sim.duree_s,
        "sim_data":    {k: v for k, v in td.items() if not k.startswith('_')},
        "gpx_base64":  td.get('_gpx_base64'),
        "ravitos_km":  td.get('_ravitos_km'),
    }


@app.put("/api/simulations/{simulation_id}")
def update_simulation(
    simulation_id: int,
    sim_data:      str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour les résultats d'une simulation épinglée (après recalcul)."""
    sim = db.query(Activity).filter(
        Activity.id == simulation_id,
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).first()

    if not sim:
        raise HTTPException(404, detail="Simulation introuvable")

    try:
        new_sim = json.loads(sim_data)
    except Exception as e:
        raise HTTPException(400, detail=f"sim_data invalide : {e}")

    # On préserve le GPX d'origine + les ravitos
    old_td = sim.trace_data or {}
    new_td = {
        **new_sim,
        '_gpx_base64': old_td.get('_gpx_base64'),
        '_ravitos_km': old_td.get('_ravitos_km'),
    }

    sim.trace_data = new_td
    sim.dist_km    = new_sim.get('distance_km', sim.dist_km)
    sim.dplus_m    = new_sim.get('dplus_m', sim.dplus_m)
    sim.duree_s    = new_sim.get('temps_total_s', sim.duree_s)

    db.commit()
    return {"status": "ok"}


@app.delete("/api/simulations/{simulation_id}")
def delete_simulation(
    simulation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime une simulation épinglée."""
    sim = db.query(Activity).filter(
        Activity.id == simulation_id,
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).first()

    if not sim:
        raise HTTPException(404, detail="Simulation introuvable")

    db.delete(sim)
    db.commit()
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════
#  BILAN : COMPARAISON RÉEL vs PRÉDIT (#9)
# ══════════════════════════════════════════════════════════════

def _temps_reels_aux_km(df, kms):
    """
    Pour un DataFrame de course réelle (avec dist_cum et duree_s),
    retourne le temps de passage cumulé réel (en secondes) à chaque km demandé.
    """
    t_cum = df['duree_s'].cumsum().values
    dist  = df['dist_cum'].values
    out = []
    for km in kms:
        # Index du point le plus proche du km demandé
        idx = int(np.abs(dist - km).argmin())
        out.append(float(t_cum[idx]))
    return out


@app.get("/api/bilan/candidats")
def bilan_candidats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retourne les éléments comparables :
    - simulations épinglées (prédictions)
    - activités de type 'resultat' (courses réellement courues)
    """
    sims = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).order_by(Activity.created_at.desc()).all()

    resultats = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.source != 'simulation',
        Activity.type_sortie == 'resultat',
    ).order_by(Activity.date_activity.desc().nullslast()).all()

    return {
        "simulations": [
            {
                "id": s.id, "name": s.name, "type_profil": s.type_profil,
                "dist_km": s.dist_km, "dplus_m": s.dplus_m, "duree_s": s.duree_s,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sims
        ],
        "resultats": [
            {
                "id": r.id, "name": r.name, "type_profil": r.type_profil,
                "dist_km": r.dist_km, "dplus_m": r.dplus_m, "duree_s": r.duree_s,
                "date": r.date_activity.isoformat() if r.date_activity else None,
            }
            for r in resultats
        ],
    }


@app.get("/api/bilan/comparer")
def bilan_comparer(
    simulation_id: int,
    resultat_id:   int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compare une simulation épinglée (prédit) à une activité résultat (réel).
    Renvoie : temps totaux, écarts par ravito, et une suggestion de coefficient.
    """
    sim = db.query(Activity).filter(
        Activity.id == simulation_id,
        Activity.user_id == user.id,
        Activity.source == 'simulation',
    ).first()
    if not sim:
        raise HTTPException(404, detail="Simulation introuvable")

    resultat = db.query(Activity).filter(
        Activity.id == resultat_id,
        Activity.user_id == user.id,
    ).first()
    if not resultat:
        raise HTTPException(404, detail="Activité résultat introuvable")

    sim_td = sim.trace_data or {}
    res_td = resultat.trace_data or {}

    # ── Distances : on compare à un point kilométrique COMMUN ──
    dist_sim = float(sim.dist_km or 0)
    dist_reel = float(resultat.dist_km or 0)
    # Le point de comparaison équitable = la plus courte des deux distances
    km_commun = min(dist_sim, dist_reel) if dist_sim > 0 and dist_reel > 0 else max(dist_sim, dist_reel)
    distances_differentes = abs(dist_sim - dist_reel) > 0.3  # tolérance 300m

    # ── Trackpoints réels (avec temps cumulé) ──
    trackpoints = res_td.get('_trackpoints', [])
    tp_avec_temps = [tp for tp in trackpoints if 't' in tp and 'dist' in tp]
    a_temps_exact = len(tp_avec_temps) > 2

    def temps_reel_au_km(km):
        """Temps de passage réel à un km donné (exact si trackpoints, sinon proportionnel)."""
        if a_temps_exact:
            proche = min(tp_avec_temps, key=lambda tp: abs(tp['dist'] - km))
            return float(proche['t'])
        # Fallback proportionnel à la distance réelle totale
        if dist_reel > 0:
            return float(resultat.duree_s or 0) * min(km / dist_reel, 1.0)
        return float(resultat.duree_s or 0)

    # ── Temps prédit & réel AU KM COMMUN ──
    ravitos_predits = sim_td.get('ravitos', []) or []

    # Temps prédit au km commun : on cherche le ravito le plus proche, sinon on prend le total
    temps_predit_total = float(sim_td.get('temps_total_s', sim.duree_s) or 0)
    if abs(km_commun - dist_sim) < 0.3:
        # km commun = fin de la simu → temps total prédit
        temps_predit = temps_predit_total
    elif ravitos_predits:
        # Interpoler le temps prédit au km commun depuis les ravitos
        rv_proche = min(ravitos_predits, key=lambda r: abs(r.get('km', 0) - km_commun))
        temps_predit = float(rv_proche.get('temps_s', temps_predit_total))
    else:
        temps_predit = temps_predit_total

    # Temps réel au km commun
    temps_reel_total = float(resultat.duree_s or 0)
    if abs(km_commun - dist_reel) < 0.3:
        temps_reel = temps_reel_total
    else:
        temps_reel = temps_reel_au_km(km_commun)

    if temps_predit <= 0:
        raise HTTPException(400, detail="La simulation n'a pas de temps prédit valide")
    if temps_reel <= 0:
        raise HTTPException(400, detail="L'activité résultat n'a pas de durée valide")

    ecart_total_s   = temps_reel - temps_predit
    ecart_total_pct = (ecart_total_s / temps_predit * 100) if temps_predit > 0 else 0

    # ── Comparaison par ravito (jusqu'au km commun seulement) ──
    comparaison_ravitos = []
    reel_dispo = False

    if ravitos_predits and temps_reel > 0 and temps_predit > 0:
        for rv in ravitos_predits:
            km = rv.get('km', 0)
            # On ne compare que les ravitos avant le point commun
            if km > km_commun + 0.3:
                continue
            t_predit = float(rv.get('temps_s', 0))
            t_reel_est = temps_reel_au_km(km)
            methode = 'exact' if a_temps_exact else 'estime'

            ecart_s = t_reel_est - t_predit
            comparaison_ravitos.append({
                "km": round(km, 1),
                "temps_predit_s": round(t_predit, 0),
                "temps_reel_s": round(t_reel_est, 0),
                "ecart_s": round(ecart_s, 0),
                "temps_predit_fmt": fmt(t_predit),
                "temps_reel_fmt": fmt(t_reel_est),
                "ecart_fmt": ("+" if ecart_s >= 0 else "−") + fmt(abs(ecart_s)),
                "plus_rapide": ecart_s < 0,
                "methode": methode,
                "is_arrivee": False,
            })
        reel_dispo = True

    # ── Ligne d'arrivée (au km commun) ──
    comparaison_ravitos.append({
        "km": round(km_commun, 1),
        "temps_predit_s": round(temps_predit, 0),
        "temps_reel_s": round(temps_reel, 0),
        "ecart_s": round(ecart_total_s, 0),
        "temps_predit_fmt": fmt(temps_predit),
        "temps_reel_fmt": fmt(temps_reel),
        "ecart_fmt": ("+" if ecart_total_s >= 0 else "−") + fmt(abs(ecart_total_s)),
        "plus_rapide": ecart_total_s < 0,
        "methode": 'exact' if a_temps_exact else 'estime',
        "is_arrivee": True,
    })

    # ── Suggestion d'ajustement du coefficient ──
    profil = db.query(Profile).filter(
        Profile.user_id == user.id,
        Profile.type == sim.type_profil,
    ).first()
    coef_actuel = float(profil.coefficient_course) if profil else 1.10

    # Le coefficient MULTIPLIE la vitesse dans la simulation :
    #   coef plus grand  → vitesse plus haute → temps plus court (plus rapide)
    #   coef plus petit  → vitesse plus basse → temps plus long  (plus lent)
    #
    # Si le réel est PLUS RAPIDE que le prédit (temps_reel < temps_predit),
    # le modèle nous sous-estimait → il faut AUGMENTER le coefficient.
    # Le bon facteur correctif est donc temps_predit / temps_reel.
    ratio_brut = temps_predit / temps_reel if temps_reel > 0 else 1.0

    # Bridage de l'ampleur : on n'applique qu'une correction PARTIELLE et bornée,
    # pour éviter les sauts violents sur une seule course (qui peut être atypique).
    # - on ne corrige que 50 % de l'écart observé (amortissement)
    # - le coefficient ne peut pas bouger de plus de ±0.08 d'un coup
    # - bornes absolues : 1.00 à 1.40
    AMORTISSEMENT = 0.5
    SAUT_MAX = 0.08
    ratio_amorti = 1.0 + (ratio_brut - 1.0) * AMORTISSEMENT
    coef_cible = coef_actuel * ratio_amorti
    delta = max(-SAUT_MAX, min(SAUT_MAX, coef_cible - coef_actuel))
    coef_suggere = float(max(COEF_MIN, min(COEF_MAX, coef_actuel + delta)))

    return {
        "simulation": {
            "id": sim.id, "name": sim.name, "type_profil": sim.type_profil,
            "dist_km": dist_sim, "dplus_m": sim.dplus_m,
            "temps_predit_s": round(temps_predit, 0),
            "temps_predit_fmt": fmt(temps_predit),
            "temps_total_s": round(temps_predit_total, 0),
            "temps_total_fmt": fmt(temps_predit_total),
        },
        "resultat": {
            "id": resultat.id, "name": resultat.name,
            "dist_km": dist_reel, "dplus_m": resultat.dplus_m,
            "temps_reel_s": round(temps_reel, 0),
            "temps_reel_fmt": fmt(temps_reel),
            "temps_total_s": round(temps_reel_total, 0),
            "temps_total_fmt": fmt(temps_reel_total),
            "date": resultat.date_activity.isoformat() if resultat.date_activity else None,
        },
        "km_commun": round(km_commun, 1),
        "distances_differentes": distances_differentes,
        "ecart_total_s": round(ecart_total_s, 0),
        "ecart_total_pct": round(ecart_total_pct, 1),
        "ecart_total_fmt": ("+" if ecart_total_s >= 0 else "−") + fmt(abs(ecart_total_s)),
        "plus_rapide": ecart_total_s < 0,
        "ravitos": comparaison_ravitos,
        "reel_dispo": reel_dispo,
        "calibration": {
            "coef_actuel": round(coef_actuel, 3),
            "coef_suggere": round(coef_suggere, 3),
            "ratio": round(ratio_brut, 3),
            "ecart_significatif": abs(coef_suggere - coef_actuel) >= 0.005,
            "resultat_dans_profil": (resultat.type_profil == sim.type_profil),
        },
    }


@app.post("/api/bilan/appliquer-calibration")
def appliquer_calibration(
    profil_type:  str   = Form(...),
    coef_suggere: float = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Applique le coefficient suggéré au profil (après validation utilisateur)."""
    if profil_type not in ("trail", "rando"):
        raise HTTPException(400, detail="profil_type doit être 'trail' ou 'rando'")
    if not (COEF_MIN <= coef_suggere <= COEF_MAX):
        raise HTTPException(400, detail="Coefficient hors limites (1.0 - 1.40)")

    profil = db.query(Profile).filter(
        Profile.user_id == user.id,
        Profile.type == profil_type,
    ).first()
    if not profil:
        raise HTTPException(404, detail="Profil introuvable")

    profil.coefficient_course = coef_suggere
    db.commit()
    return {"status": "ok", "coefficient_course": coef_suggere}


@app.post("/api/bilan/pin")
def pin_bilan(
    nom:           str = Form(...),
    simulation_id: int = Form(...),
    resultat_id:   int = Form(...),
    bilan_json:    str = Form(...),
    commentaire:   str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Épingle un bilan (comparaison réel vs prédit) pour le retrouver plus tard."""
    count = db.query(BilanResultat).filter(BilanResultat.user_id == user.id).count()
    if count >= 30:
        raise HTTPException(400, detail="Limite de 30 bilans épinglés atteinte.")

    try:
        bilan = json.loads(bilan_json)
    except Exception as e:
        raise HTTPException(400, detail=f"bilan_json invalide : {e}")

    b = BilanResultat(
        user_id       = user.id,
        nom           = nom.strip()[:200] or "Bilan",
        simulation_id = simulation_id,
        resultat_id   = resultat_id,
        type_profil   = bilan.get('simulation', {}).get('type_profil', 'trail'),
        bilan_data    = bilan,
        commentaire   = (commentaire or '').strip()[:2000] or None,
        ecart_total_s = float(bilan.get('ecart_total_s', 0) or 0),
        plus_rapide   = bool(bilan.get('plus_rapide', False)),
        km_commun     = float(bilan.get('km_commun', 0) or 0),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"status": "ok", "bilan_id": b.id}


@app.patch("/api/bilan/pinned/{bilan_id}")
def update_bilan(
    bilan_id:    int,
    commentaire: Optional[str] = Form(None),
    nom:         Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour le commentaire et/ou le nom d'un bilan épinglé."""
    b = db.query(BilanResultat).filter(
        BilanResultat.id == bilan_id,
        BilanResultat.user_id == user.id,
    ).first()
    if not b:
        raise HTTPException(404, detail="Bilan introuvable")

    if commentaire is not None:
        b.commentaire = commentaire.strip()[:2000] or None
    if nom is not None and nom.strip():
        b.nom = nom.strip()[:200]

    db.commit()
    return {"status": "ok", "commentaire": b.commentaire, "nom": b.nom}


@app.get("/api/bilan/pinned")
def list_bilans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste les bilans épinglés."""
    bilans = db.query(BilanResultat).filter(
        BilanResultat.user_id == user.id,
    ).order_by(BilanResultat.created_at.desc()).all()

    return {
        "bilans": [
            {
                "id": b.id,
                "nom": b.nom,
                "commentaire": b.commentaire,
                "ecart_total_s": b.ecart_total_s,
                "ecart_fmt": ("+" if b.ecart_total_s >= 0 else "−") + fmt(abs(b.ecart_total_s)),
                "plus_rapide": b.plus_rapide,
                "km_commun": b.km_commun,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "bilan_data": b.bilan_data,
            }
            for b in bilans
        ]
    }


@app.delete("/api/bilan/pinned/{bilan_id}")
def delete_bilan(
    bilan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime un bilan épinglé."""
    b = db.query(BilanResultat).filter(
        BilanResultat.id == bilan_id,
        BilanResultat.user_id == user.id,
    ).first()
    if not b:
        raise HTTPException(404, detail="Bilan introuvable")
    db.delete(b)
    db.commit()
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════
#  INITIALISATION DE LA BASE AU DÉMARRAGE
# ══════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    init_db()


# ══════════════════════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════════════════════

if __name__=="__main__":
    import uvicorn
    print("\n"+"="*55)
    print("  🏔️  SUM'IT API — Plan your peaks")
    print("="*55)
    print("  Serveur : http://localhost:8000")
    print("  Docs    : http://localhost:8000/docs")
    print("="*55+"\n")
    uvicorn.run("api:app",host="0.0.0.0",port=8000,reload=True)
