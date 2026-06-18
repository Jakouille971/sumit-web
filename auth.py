# ══════════════════════════════════════════════════════════════
#  SUM'IT — auth.py
#  Authentification : Google OAuth + JWT
# ══════════════════════════════════════════════════════════════

import os
import jwt
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from db import User, get_db

# ── Configuration ──────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET           = os.getenv("JWT_SECRET", "fallback-dev-secret-change-me")
JWT_ALGORITHM        = "HS256"
JWT_EXPIRE_DAYS      = 30

# URLs
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

# Le redirect URI est ce que Google va appeler après authentification
# Détection auto local vs prod via une variable d'environnement
API_BASE_URL = os.getenv("API_BASE_URL", "https://sumit-web-s4lf.onrender.com")
GOOGLE_REDIRECT_URI = f"{API_BASE_URL}/api/auth/google/callback"

# URL frontend pour rediriger après login
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://sumit-web-nine.vercel.app")


# ══════════════════════════════════════════════════════════════
#  JWT — Création & validation des tokens
# ══════════════════════════════════════════════════════════════

def creer_jwt(user_id: int, email: str) -> str:
    """Crée un JWT signé pour un utilisateur."""
    payload = {
        "user_id": user_id,
        "email":   email,
        "exp":     datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
        "iat":     datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decoder_jwt(token: str) -> dict:
    """Décode et valide un JWT. Lève HTTPException si invalide."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expiré, reconnecte-toi")
    except jwt.InvalidTokenError:
        raise HTTPException(401, detail="Token invalide")


# ══════════════════════════════════════════════════════════════
#  Dépendance FastAPI : utilisateur authentifié
# ══════════════════════════════════════════════════════════════

def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Vérifie le JWT dans le header Authorization et retourne l'utilisateur.
    Usage :
        @app.get("/api/me")
        def me(user: User = Depends(get_current_user)):
            return user
    """
    if not authorization:
        raise HTTPException(401, detail="Token manquant")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="Format token invalide (Bearer attendu)")

    token = authorization.replace("Bearer ", "")
    payload = decoder_jwt(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(401, detail="Token sans user_id")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, detail="Utilisateur introuvable")

    return user


def get_current_user_optional(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User | None:
    """Version qui ne lève pas d'erreur si pas authentifié."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.replace("Bearer ", "")
        payload = decoder_jwt(token)
        return db.query(User).filter(User.id == payload.get("user_id")).first()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  Google OAuth — Échange de code contre user info
# ══════════════════════════════════════════════════════════════

def construire_url_google_auth() -> str:
    """Construit l'URL Google de redirection pour démarrer le flow OAuth."""
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
        "prompt":        "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def echanger_code_google(code: str) -> dict:
    """
    Échange le code Google contre un access_token, puis récupère les
    infos utilisateur (email, name, picture, google_id).
    """
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Échanger code → access_token
        token_data = {
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        }
        token_res = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        if token_res.status_code != 200:
            raise HTTPException(400, detail=f"Échec OAuth Google: {token_res.text}")

        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(400, detail="Pas d'access_token Google reçu")

        # 2. Récupérer les infos user
        user_res = await client.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_res.status_code != 200:
            raise HTTPException(400, detail="Impossible de récupérer infos Google")

        return user_res.json()


def upsert_user_google(db: Session, google_user: dict) -> User:
    """
    Crée ou met à jour un utilisateur depuis les infos Google.
    google_user contient : sub (google_id), email, name, picture
    """
    google_id = google_user.get("sub")
    email     = google_user.get("email")
    name      = google_user.get("name")
    picture   = google_user.get("picture")

    if not google_id or not email:
        raise HTTPException(400, detail="Infos Google incomplètes")

    user = db.query(User).filter(User.google_id == google_id).first()

    if user:
        # Mise à jour des infos (nom/photo peuvent changer)
        user.email      = email
        user.name       = name
        user.picture    = picture
        user.last_login = datetime.now(timezone.utc)
    else:
        # Création nouveau compte
        prenom_auto = name.split(" ")[0] if name else "Coureur"
        user = User(
            google_id  = google_id,
            email      = email,
            name       = name,
            picture    = picture,
            prenom     = prenom_auto,
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user
