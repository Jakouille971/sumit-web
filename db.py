# ══════════════════════════════════════════════════════════════
#  SUM'IT — db.py
#  Connexion BDD PostgreSQL (Neon) + Modèles SQLAlchemy
# ══════════════════════════════════════════════════════════════

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func

# ── Configuration ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sumit.db")

# Render fournit DATABASE_URL au format postgres:// mais SQLAlchemy 2.x veut postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Neon requiert sslmode=require, déjà dans l'URL en général
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # vérifie que la connexion est encore vivante
    pool_recycle=300,    # recrée la connexion toutes les 5 min
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ══════════════════════════════════════════════════════════════
#  MODÈLES
# ══════════════════════════════════════════════════════════════

class User(Base):
    """Compte utilisateur (créé via Google OAuth)."""
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    google_id     = Column(String, unique=True, index=True, nullable=False)
    email         = Column(String, unique=True, index=True, nullable=False)
    name          = Column(String, nullable=True)
    picture       = Column(String, nullable=True)
    prenom        = Column(String, nullable=True)  # prénom personnalisable
    fcmax         = Column(Integer, default=193)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login    = Column(DateTime(timezone=True), server_default=func.now())

    # Tokens Strava (pour import automatique)
    strava_athlete_id     = Column(String, nullable=True, index=True)
    strava_access_token   = Column(String, nullable=True)
    strava_refresh_token  = Column(String, nullable=True)
    strava_token_expires  = Column(DateTime(timezone=True), nullable=True)

    # Relations
    profiles   = relationship("Profile",   back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity",  back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    """
    Profil coureur : un utilisateur peut avoir 2 profils (Trail, Rando).
    Contient les VEP par terrain, archétype, drain énergétique, etc.
    """
    __tablename__ = "profiles"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type         = Column(String, nullable=False)  # 'trail' ou 'rando'

    # Données du profil (JSON pour flexibilité)
    profil_data  = Column(JSON, nullable=False, default=dict)
    archetype    = Column(JSON, nullable=True)
    coefficient_course = Column(Float, default=1.0)
    drain_moy_h        = Column(Float, default=0.08)
    vep_globale        = Column(Float, default=0.0)
    nb_traces          = Column(Integer, default=0)

    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profiles")


class Activity(Base):
    """
    Activité GPX importée (Strava ou manuelle).
    Stockée pour permettre de reconstruire le profil incrémentalement.
    """
    __tablename__ = "activities"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Source
    source        = Column(String, nullable=False, default='manual')  # 'manual', 'strava'
    external_id   = Column(String, nullable=True, index=True)  # ID Strava si applicable

    # Métadonnées
    name          = Column(String, nullable=True)
    type_sortie   = Column(String, default='entrainement')  # 'course', 'entrainement', 'sortie'
    type_profil   = Column(String, default='trail')  # 'trail' ou 'rando'
    date_activity = Column(DateTime(timezone=True), nullable=True)

    # Données calculées (résumé pour affichage rapide)
    dist_km       = Column(Float, default=0.0)
    dplus_m       = Column(Float, default=0.0)
    duree_s       = Column(Integer, default=0)
    vep_globale   = Column(Float, default=0.0)

    # Données complètes pour re-calcul (compactes : JSON sérialisé)
    trace_data    = Column(JSON, nullable=True)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="activities")


class ProfilSnapshot(Base):
    """
    Historique du profil après chaque ajout/suppression d'activité.
    Permet de tracer l'évolution VEP/drain/coef/scores/archétype dans le temps.
    """
    __tablename__ = "profil_snapshots"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type_profil   = Column(String, nullable=False, index=True)  # 'trail' ou 'rando'

    # Lien optionnel vers l'activité ajoutée qui a déclenché le snapshot
    activity_id   = Column(Integer, ForeignKey("activities.id"), nullable=True)

    date_activity = Column(DateTime(timezone=True), nullable=True, index=True)

    # Métriques agrégées au moment du snapshot
    vep_globale       = Column(Float, default=0.0)
    drain_moy_h       = Column(Float, default=0.0)
    coefficient_course= Column(Float, default=1.0)
    nb_traces         = Column(Integer, default=0)
    dist_moy_km       = Column(Float, default=0.0)

    # Scores de pente
    score_montee      = Column(Float, default=0.0)  # ecart_plat moyen montées
    score_descente    = Column(Float, default=0.0)  # ecart_plat moyen descentes

    # Archétype (chaîne pour color-coding)
    archetype_nom     = Column(String, nullable=True)

    created_at        = Column(DateTime(timezone=True), server_default=func.now())


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Base de données initialisée")
    except Exception as e:
        print(f"❌ Erreur init BDD : {e}")


def get_db():
    """Generator pour les dépendances FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
