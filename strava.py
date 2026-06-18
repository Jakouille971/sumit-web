# ══════════════════════════════════════════════════════════════
#  SUM'IT — strava.py
#  Intégration Strava : OAuth + import des activités
# ══════════════════════════════════════════════════════════════

import os
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from db import User

# ── Configuration ──────────────────────────────────────────────
STRAVA_CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

STRAVA_AUTH_URL  = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE  = "https://www.strava.com/api/v3"

API_BASE_URL = os.getenv("API_BASE_URL", "https://sumit-web-s4lf.onrender.com")
STRAVA_REDIRECT_URI = f"{API_BASE_URL}/api/strava/callback"

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://sumit-web-nine.vercel.app")


# ══════════════════════════════════════════════════════════════
#  OAuth — Connexion Strava
# ══════════════════════════════════════════════════════════════

def construire_url_strava_auth(state: str = "") -> str:
    """
    Construit l'URL Strava pour démarrer la connexion.
    state : token JWT du user pour le retrouver dans le callback.
    """
    params = {
        "client_id":     STRAVA_CLIENT_ID,
        "redirect_uri":  STRAVA_REDIRECT_URI,
        "response_type": "code",
        "scope":         "read,activity:read_all",  # lecture des activités
        "approval_prompt": "force",
        "state":         state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{STRAVA_AUTH_URL}?{query}"


async def echanger_code_strava(code: str) -> dict:
    """Échange le code Strava contre un access/refresh token."""
    async with httpx.AsyncClient(timeout=10) as client:
        data = {
            "client_id":     STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "code":          code,
            "grant_type":    "authorization_code",
        }
        res = await client.post(STRAVA_TOKEN_URL, data=data)
        if res.status_code != 200:
            raise HTTPException(400, detail=f"Échec OAuth Strava: {res.text}")
        return res.json()


def sauvegarder_tokens_strava(db: Session, user: User, token_data: dict):
    """Sauvegarde les tokens Strava dans le User."""
    athlete = token_data.get("athlete", {})
    expires_at = token_data.get("expires_at")  # timestamp UNIX

    user.strava_athlete_id    = str(athlete.get("id"))
    user.strava_access_token  = token_data.get("access_token")
    user.strava_refresh_token = token_data.get("refresh_token")
    if expires_at:
        user.strava_token_expires = datetime.fromtimestamp(expires_at, tz=timezone.utc)

    db.commit()


# ══════════════════════════════════════════════════════════════
#  Rafraîchissement du token
# ══════════════════════════════════════════════════════════════

async def rafraichir_token_strava(db: Session, user: User) -> str:
    """
    Vérifie si le token Strava est expiré, et le rafraîchit si besoin.
    Retourne un access_token valide.
    """
    now = datetime.now(timezone.utc)

    if not user.strava_refresh_token:
        raise HTTPException(401, detail="Compte Strava non connecté")

    # Token encore valide (avec marge 60s) ?
    if user.strava_token_expires and user.strava_token_expires > now + timedelta(seconds=60):
        return user.strava_access_token

    # Rafraîchir
    async with httpx.AsyncClient(timeout=10) as client:
        data = {
            "client_id":     STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": user.strava_refresh_token,
            "grant_type":    "refresh_token",
        }
        res = await client.post(STRAVA_TOKEN_URL, data=data)
        if res.status_code != 200:
            raise HTTPException(401, detail="Token Strava expiré, reconnecte-toi")

        new_data = res.json()
        user.strava_access_token  = new_data.get("access_token")
        user.strava_refresh_token = new_data.get("refresh_token")
        user.strava_token_expires = datetime.fromtimestamp(new_data["expires_at"], tz=timezone.utc)
        db.commit()
        return user.strava_access_token


# ══════════════════════════════════════════════════════════════
#  Liste des activités du user
# ══════════════════════════════════════════════════════════════

async def lister_activites_strava(db: Session, user: User, per_page: int = 30, page: int = 1):
    """
    Récupère les activités Strava récentes du user.
    Filtre sur Run/TrailRun/Hike (compatible trail/rando).
    """
    access_token = await rafraichir_token_strava(db, user)

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"per_page": per_page, "page": page},
        )
        if res.status_code != 200:
            raise HTTPException(res.status_code, detail=f"Erreur API Strava: {res.text}")

        activities = res.json()

        # Filtrer Run / TrailRun / Hike
        filtered = [
            a for a in activities
            if a.get("type") in ("Run", "TrailRun", "Hike", "Walk")
        ]

        return [
            {
                "id":              str(a["id"]),
                "name":            a.get("name"),
                "type":            a.get("type"),
                "sport_type":      a.get("sport_type"),
                "date":            a.get("start_date_local"),
                "distance_km":     round(a.get("distance", 0) / 1000, 2),
                "dplus_m":         a.get("total_elevation_gain", 0),
                "duree_s":         a.get("moving_time", 0),
                "average_speed":   round(a.get("average_speed", 0) * 3.6, 2),  # m/s → km/h
                "has_heartrate":   a.get("has_heartrate", False),
            }
            for a in filtered
        ]


# ══════════════════════════════════════════════════════════════
#  Téléchargement du GPX d'une activité
# ══════════════════════════════════════════════════════════════

async def telecharger_gpx_strava(db: Session, user: User, activity_id: str) -> bytes:
    """
    Récupère les streams (lat/lon/altitude/temps/FC) d'une activité,
    et reconstruit un GPX exploitable par charger_gpx().

    Note : l'API Strava ne fournit pas de GPX direct. Il faut reconstruire
    depuis les streams.
    """
    access_token = await rafraichir_token_strava(db, user)

    async with httpx.AsyncClient(timeout=30) as client:
        # Streams : latlng, altitude, time, heartrate
        res = await client.get(
            f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "keys": "latlng,altitude,time,heartrate",
                "key_by_type": "true",
            },
        )
        if res.status_code != 200:
            raise HTTPException(res.status_code, detail=f"Erreur streams Strava: {res.text}")

        streams = res.json()

        # Récupérer les données du start_date pour avoir le départ
        activity_res = await client.get(
            f"{STRAVA_API_BASE}/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        activity_meta = activity_res.json() if activity_res.status_code == 200 else {}

    return construire_gpx_depuis_streams(streams, activity_meta)


def construire_gpx_depuis_streams(streams: dict, meta: dict) -> bytes:
    """
    Construit un fichier GPX à partir des streams Strava.
    """
    latlng    = streams.get("latlng",    {}).get("data", [])
    altitude  = streams.get("altitude",  {}).get("data", [])
    time_offs = streams.get("time",      {}).get("data", [])
    hr        = streams.get("heartrate", {}).get("data", [])

    if not latlng:
        raise HTTPException(400, detail="Pas de données GPS dans cette activité")

    # Date de départ
    start_date_str = meta.get("start_date", datetime.now(timezone.utc).isoformat())
    try:
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    except Exception:
        start_date = datetime.now(timezone.utc)

    activity_name = meta.get("name", "Activité Strava")

    # Construire le XML GPX
    gpx_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="SUMIT-Strava" xmlns="http://www.topografix.com/GPX/1/1">',
        '<trk>',
        f'<name>{activity_name}</name>',
        '<trkseg>',
    ]

    has_hr = len(hr) == len(latlng)

    for i, (lat, lon) in enumerate(latlng):
        alt   = altitude[i]  if i < len(altitude)  else 0
        toff  = time_offs[i] if i < len(time_offs) else 0
        time_pt = start_date + timedelta(seconds=int(toff))
        time_str = time_pt.strftime("%Y-%m-%dT%H:%M:%SZ")

        gpx_lines.append(f'<trkpt lat="{lat}" lon="{lon}">')
        gpx_lines.append(f'<ele>{alt}</ele>')
        gpx_lines.append(f'<time>{time_str}</time>')

        if has_hr:
            gpx_lines.append('<extensions>')
            gpx_lines.append('<gpxtpx:TrackPointExtension xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">')
            gpx_lines.append(f'<gpxtpx:hr>{hr[i]}</gpxtpx:hr>')
            gpx_lines.append('</gpxtpx:TrackPointExtension>')
            gpx_lines.append('</extensions>')

        gpx_lines.append('</trkpt>')

    gpx_lines.append('</trkseg>')
    gpx_lines.append('</trk>')
    gpx_lines.append('</gpx>')

    return "\n".join(gpx_lines).encode("utf-8")
