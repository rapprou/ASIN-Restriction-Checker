import os
from dotenv import load_dotenv

load_dotenv()

LWA_CLIENT_ID = os.getenv("LWA_CLIENT_ID")
LWA_CLIENT_SECRET = os.getenv("LWA_CLIENT_SECRET")
LWA_REFRESH_TOKEN = os.getenv("LWA_REFRESH_TOKEN")
SELLER_ID = os.getenv("SELLER_ID")
MARKETPLACE_ID = os.getenv("MARKETPLACE_ID", "A13V1IB3VIYZZH")

# --- Auth JWT ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Compte admin unique (pas de table users pour l'instant)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")  # généré via passlib, jamais en clair