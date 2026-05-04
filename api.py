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
    df['alt']=df['alt'].rolling(30,center=True,min_periods=1).mean()
    df['dz']=df['alt'].diff().fillna(0)
    df['dp']=df['dz'].clip(lower=0)
    df['dm']=df['dz'].clip(upper=0).abs()

    # Exclure arrêts
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
    fe,pe,fc_,pc=[],[],[],[]
    for t in traces:
        r=t.get('fc_ratio_moy')
        if r is None: continue
        d=t['dist_km']
        if t['type_sortie']=='entrainement': fe.append(r);pe.append(d)
        elif t['type_sortie']=='course':     fc_.append(r);pc.append(d)
    me=float(np.average(fe,weights=pe)) if fe else 0.75
    mc=float(np.average(fc_,weights=pc)) if fc_ else cible
    c=float(max(1.05,min(1.30,mc/me if me>0 else 1.10)))
    return {
        'coefficient':round(c,3),'gain_pct':round((c-1)*100,1),
        'fc_moy_entrainement':round(me,3),'fc_course_utilisee':round(mc,3),
        'nb_entrainements':len(fe),'nb_courses_reelles':len(fc_),
        'calibre_sur_courses':len(fc_)>0
    }

# ══════════════════════════════════════════════════════════════
#  AGRÉGATION PROFIL
# ══════════════════════════════════════════════════════════════

def agreger(traces):
    profil={}
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
            'vep_norm':round(va,2),'vep_std':round(float(np.std(vs)),2),
            'score':min(100,max(0,round((va/REF_VEP[t])*50))),
            'nb_courses':len(vs),
            'f_basse':round(float(max(0.05,cm*0.8)),3),
            'f_haute':round(float(min(0.30,cm*1.2)),3),
        }
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
    tm=[t for t in ['montee_raide','montee_soutenue','montee_douce'] if t in profil]
    td=[t for t in ['descente_douce','descente_soutenue','descente_raide'] if t in profil]
    sm=float(np.mean([profil[t]['score'] for t in tm])) if tm else 50
    sd=float(np.mean([profil[t]['score'] for t in td])) if td else 50
    sp=float(profil.get('plat',{}).get('score',50))
    sc=[profil[t]['score'] for t in profil]
    sr=100-float(np.std(sc))*2 if sc else 50
    if sm>=65 and sm>sd+15:
        return {'key':'grimpeur','nom':'Le Grimpeur',
                'desc':"Tu avales les D+ comme personne.",
                'forces':['Montées raides et soutenues',"Résistance à l'accumulation de D+"],
                'faiblesses':['Descentes techniques','Manque de vitesse sur plat'],
                'conseil':'Travaille tes descentes en fractionné technique.'}
    elif sd>=65 and sd>sm+15:
        return {'key':'descendeur','nom':'Le Descendeur',
                'desc':"Tu récupères dans les descentes.",
                'forces':['Descentes rapides et fluides','Technique sur terrain varié'],
                'faiblesses':['Montées longues','Accumulation de D+'],
                'conseil':'Intègre des montées spécifiques à tes entraînements.'}
    elif sp>=65 and sp>sm and sp>sd:
        return {'key':'explosif','nom':"L'Explosif",
                'desc':"Tu es à l'aise sur le plat et les sections roulantes.",
                'forces':['Sections rapides','Vitesse de base élevée'],
                'faiblesses':["Fatigue sur longs D+","Manque d'efficacité en altitude"],
                'conseil':'Développe ta puissance en côte.'}
    elif sr>=70 and max(sm,sd,sp)-min(sm,sd,sp)<20:
        return {'key':'equilibre','nom':"L'Équilibré",
                'desc':'Profil homogène sur tous les terrains.',
                'forces':['Polyvalence',"Régularité de l'allure"],
                'faiblesses':['Pas de point fort dominant','Surclassé par des spécialistes'],
                'conseil':'Choisis des parcours variés. Travaille un point fort.'}
    else:
        return {'key':'tenace','nom':'Le Tenace',
                'desc':"Tu ne lâches jamais.",
                'forces':["Gestion de l'effort",'Mental et régularité'],
                'faiblesses':['Vitesse de pointe limitée',"Moins à l'aise sur les courts"],
                'conseil':'Fais-toi plaisir sur les ultras.'}

# ══════════════════════════════════════════════════════════════
#  SIMULATION
# ══════════════════════════════════════════════════════════════

def simuler(df, profil, drain_h, cat, coeff=1.0):
    dep_tot=float(df['dep_m'].sum())
    dp_tot =float(df['dp_cum'].max())
    batt=100.0
    drain_s=drain_h/3600
    dep=0.0
    t=0.0
    res=[]
    for _,row in df.iterrows():
        if row['dist_m']==0: continue
        dep+=float(row['dep_m'])
        tr=row['terrain']
        vn=profil.get(tr,{}).get('vep_norm',REF_VEP.get(tr,7.0))
        vr=vn*cat['facteur']*coeff
        rd=float(row['dp_cum'])/dp_tot if dp_tot>0 else 0
        cm=1.0 if rd<=0.5 else 1.0-0.15*((rd-0.5)/0.5)
        br=batt/100
        cb=1.0 if br>=0.5 else 1.0-0.25*((0.5-br)/0.5)
        ct=cm*cb
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

    # Simulation
    res=simuler(df,profil,drain_moy_h,cat,coefficient)
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
    chart=sdf.iloc[::step][['dist_km','altitude','terrain','vitesse_kmh','batterie_pct']].round(2).to_dict('records')

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
