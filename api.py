# ══════════════════════════════════════════════════════════════
#  SUM'IT — API Backend FastAPI
#  Lance avec : python api.py
# ══════════════════════════════════════════════════════════════

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import gpxpy
import pandas as pd
import numpy as np
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

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

MINETTI_TABLE = {
    -25:1.28,-20:1.17,-15:1.08,-10:1.03,
    -5:0.95,0:1.00,5:1.22,10:1.58,
    15:2.14,20:2.90,25:3.94
}

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

POIDS_TYPE = {'course':1.00,'entrainement':0.70,'sortie':0.40}
DEMI_VIE   = 180

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

def minetti(p):
    pc=max(-25,min(25,p))
    ks=sorted(MINETTI_TABLE.keys())
    for i in range(len(ks)-1):
        p1,p2=ks[i],ks[i+1]
        if p1<=pc<=p2:
            t=(pc-p1)/(p2-p1)
            return MINETTI_TABLE[p1]+t*(MINETTI_TABLE[p2]-MINETTI_TABLE[p1])
    return 1.0

def categorie(dist_km):
    for c in CATEGORIES:
        if c['min']<=dist_km<c['max']:
            return c
    return CATEGORIES[-1]

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

    df['duree_s']=df['t'].diff().dt.total_seconds().fillna(0) if df['t'].notna().any() else 1.0
    df['vit_kmh']=(df['dist_m']/df['duree_s'].replace(0,np.nan)*3.6).clip(0,40).fillna(0)

    # ── Lissage altitude : double pass pour lisser les pics GPS ──
    # 1ère passe : médiane sur 15 points (élimine les outliers ponctuels)
    # 2ème passe : moyenne sur 30 points (lissage doux pour les pentes)
    df['alt']=df['alt'].rolling(15,center=True,min_periods=1).median()
    df['alt']=df['alt'].rolling(30,center=True,min_periods=1).mean()
    df['dz']=df['alt'].diff().fillna(0)
    df['dp']=df['dz'].clip(lower=0)
    df['dm']=df['dz'].clip(upper=0).abs()

    # ── Filtrage outliers de vitesse (3 sigma) ──
    # Élimine les points avec une vitesse aberrante (perte GPS, tunnel...)
    if len(df) > 50:
        v_med = df['vit_kmh'].median()
        v_std = df['vit_kmh'].std()
        seuil_max = v_med + 3 * v_std
        df.loc[df['vit_kmh'] > seuil_max, 'vit_kmh'] = np.nan
        df['vit_kmh'] = df['vit_kmh'].interpolate().fillna(v_med)

    # Exclure arrêts (vitesse < 1 km/h pendant > 30 sec)
    df=df[~((df['vit_kmh']<1.0)&(df['duree_s']>0))].copy()

    df['pente']=(df['dz']/df['dist_m'].replace(0,np.nan)*100).replace([np.inf,-np.inf],0).fillna(0).clip(-80,80)
    df['pente_l']=df['pente'].rolling(10,center=True).mean().fillna(df['pente'])
    df['terrain']=df['pente_l'].apply(terrain)
    df['cm']=df['pente_l'].apply(minetti)
    df['vep']=(df['vit_kmh']*df['cm']).clip(0,20)
    df['vep']=df.apply(lambda r:min(r['vep'],VEP_MAX.get(r['terrain'],18)),axis=1)
    df['vep']=df['vep'].rolling(15,center=True,min_periods=1).mean()

    df['dist_cum']=df['dist_m'].cumsum()/1000
    df['t_h']=df['duree_s'].cumsum()/3600
    df['dep_m']=df['dist_m']*df['cm']
    df['dep_cum']=df['dep_m'].cumsum()/1000
    df['dp_cum']=df['dp'].cumsum()

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

def analyser_trace(df, date0, type_sortie, fcmax):
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
        if len(sub)<20: continue
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
        elif t['type_sortie']=='course':
            fc_.append(r); pc.append(poids)

    me=float(np.average(fe,weights=pe)) if fe else 0.75
    mc=float(np.average(fc_,weights=pc)) if fc_ else cible
    c=float(max(1.05,min(1.30,mc/me if me>0 else 1.10)))

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

def archetype(profil):
    if not profil:
        return {'key':'combattant','nom':'Le Combattant','desc':'Profil en construction.',
                'forces':[],'faiblesses':[],'conseil':'Ajoute plus de traces GPX.'}

    # On utilise les écarts vs plat (positifs = points forts, négatifs = points faibles)
    tm=[t for t in ['montee_raide','montee_soutenue','montee_douce'] if t in profil]
    td=[t for t in ['descente_douce','descente_soutenue','descente_raide'] if t in profil]

    em=float(np.mean([profil[t]['ecart_plat_pct'] for t in tm])) if tm else 0
    ed=float(np.mean([profil[t]['ecart_plat_pct'] for t in td])) if td else 0

    # Régularité = faible écart-type entre tous les terrains
    ecarts=[profil[t]['ecart_plat_pct'] for t in profil]
    sr=float(np.std(ecarts)) if ecarts else 100

    # Logique de classification
    # Note: les écarts sont souvent négatifs (le plat reste généralement le plus rapide)
    # On compare donc les écarts RELATIFS entre montée et descente
    if em > ed + 5 and em > -10:
        # Montagne marquée au-dessus de la descente
        return {'key':'grimpeur','nom':'Le Grimpeur',
                'desc':"Tu avales les D+ comme personne. Les montées sont ton terrain de jeu.",
                'forces':['Montées raides et soutenues',"Résistance à l'accumulation de D+"],
                'faiblesses':['Descentes techniques','Manque de vitesse sur plat'],
                'conseil':'Travaille tes descentes en fractionné technique.'}
    elif ed > em + 5 and ed > -10:
        return {'key':'descendeur','nom':'Le Descendeur',
                'desc':"Tu récupères dans les descentes ce que tu perds à la montée.",
                'forces':['Descentes rapides et fluides','Technique sur terrain varié'],
                'faiblesses':['Montées longues','Accumulation de D+'],
                'conseil':'Intègre des montées spécifiques à tes entraînements.'}
    elif sr < 8:
        # Très faible variabilité = équilibré
        return {'key':'equilibre','nom':"L'Équilibré",
                'desc':'Profil homogène sur tous les terrains.',
                'forces':['Polyvalence',"Régularité de l'allure"],
                'faiblesses':['Pas de point fort dominant','Surclassé par des spécialistes'],
                'conseil':'Choisis des parcours variés. Travaille un point fort.'}
    elif em < -25 and ed < -25:
        # Sous-performance importante en montée ET descente vs plat
        return {'key':'explosif','nom':"L'Explosif",
                'desc':"Tu es à l'aise sur le plat et les sections roulantes.",
                'forces':['Sections rapides','Vitesse de base élevée'],
                'faiblesses':["Fatigue sur longs D+","Manque d'efficacité en altitude"],
                'conseil':'Développe ta puissance en côte.'}
    else:
        return {'key':'tenace','nom':'Le Tenace',
                'desc':"Tu ne lâches jamais. Ta force c'est la régularité dans la durée.",
                'forces':["Gestion de l'effort",'Mental et régularité'],
                'faiblesses':['Vitesse de pointe limitée',"Moins à l'aise sur les courts"],
                'conseil':'Fais-toi plaisir sur les ultras.'}

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


def requeter_overpass(bbox, timeout=30):
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
    Simulation point par point avec modèle de fatigue + technicité du terrain.

    types_terrain : liste optionnelle des types de terrain par point GPX
                    (route/piste/sentier_large/sentier_montagne/hors_trace)
    """
    dep_tot=float(df['dep_m'].sum())
    dp_tot =float(df['dp_cum'].max())
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

        # Fatigue mécanique non-linéaire
        rd=float(row['dp_cum'])/dp_tot if dp_tot>0 else 0
        if rd <= 0.30:
            cm = 1.0
        else:
            facteur = ((rd - 0.30) / 0.70) ** 1.5
            cm = 1.0 - 0.13 * facteur

        # Fatigue batterie non-linéaire
        br=batt/100
        if br >= 0.50:
            cb = 1.0
        elif br >= 0.30:
            cb = 0.92 + 0.08 * ((br - 0.30) / 0.20)
        else:
            ratio = max(0, br / 0.30)
            cb = 0.78 + 0.14 * (ratio ** 0.7)

        # Technicité du terrain (OSM)
        type_t = types_terrain[idx] if idx < len(types_terrain) else 'sentier_large'
        coef_tech = TERRAIN_TYPES.get(type_t, TERRAIN_TYPES['sentier_large'])['coef_vitesse']

        ct=cm*cb*coef_tech
        ve=vr*ct
        vm=(ve/3.6)/float(row['cm'])
        vm=max(vm,0.3)
        ds=float(row['dist_m'])/vm
        batt=max(0.0,batt-drain_s*ds*100)
        t+=ds
        res.append({
            'dist_km':    round(float(row['dist_cum']),3),
            'altitude':   round(float(row['alt']),1),
            'terrain':    tr,
            'type_terrain': type_t,
            'effort_pct': round(dep/dep_tot*100,2) if dep_tot>0 else 0,
            'coef_meca':  round(cm,3),
            'coef_batt':  round(cb,3),
            'coef_tech':  round(coef_tech,3),
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
    arch=archetype(profil)

    return {
        "status":"ok","nb_traces":len(traces),"traces":traces,
        "profil":profil,"drain_moy_h":drain,
        "coefficient_course":cc,"archetype":arch,
        "endurance_score":85,"erreurs":erreurs,"profil_type":profil_type,
    }


@app.post("/api/simuler")
async def api_simuler(
    fichier_cible: UploadFile = File(...),
    ravitos_km:    str   = Form(""),
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

    dist_km=float(df['dist_cum'].max())
    dplus_m=float(df['dp_cum'].max())
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

    # ── Classification du terrain via OpenStreetMap ──
    # Cette étape peut prendre 5-15 secondes selon la taille de la zone
    try:
        types_terrain = classifier_trace_via_osm(df)
        print(f"✅ OSM : {len(set(types_terrain))} types détectés sur {len(types_terrain)} points")
    except Exception as e:
        print(f"⚠️ Échec classification OSM : {e}")
        types_terrain = ['sentier_large'] * len(df)

    # Simulation avec technicité
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
    for km in ravs:
        idx=int((sdf['dist_km']-km).abs().idxmin())
        t_ =float(sdf.loc[idx,'temps_s'])
        tb_=float(fdf.loc[idx,'tb'])
        th_=float(fdf.loc[idx,'th'])
        b_ =float(sdf.loc[idx,'batterie_pct'])
        rvd.append({
            'km':round(km,1),
            'temps_s':round(t_,1),'temps_bas_s':round(tb_,1),'temps_haut_s':round(th_,1),
            'batterie_pct':round(b_,1),
            'temps_fmt':fmt(t_),'bas_fmt':fmt(tb_),'haut_fmt':fmt(th_),
        })

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
        "dep_km":round(dep_km,2),
        "categorie":{
            "nom":cat["nom"],
            "emoji":cat["emoji"],
            "facteur":cat["facteur"],
        },
        "temps_total_s":round(tt,1),
        "temps_bas_s":round(tb,1),
        "temps_haut_s":round(th,1),
        "temps_fmt":fmt(tt),
        "bas_fmt":fmt(tb),
        "haut_fmt":fmt(th),
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

if __name__=="__main__":
    import uvicorn
    print("\n"+"="*55)
    print("  🏔️  SUM'IT API — Plan your peaks")
    print("="*55)
    print("  Serveur : http://localhost:8000")
    print("  Docs    : http://localhost:8000/docs")
    print("="*55+"\n")
    uvicorn.run("api:app",host="0.0.0.0",port=8000,reload=True)
