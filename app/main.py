from fastapi import FastAPI
from app.routers import asin, auth

app = FastAPI(
    title="ASIN Restriction Checker API",
    description="Vérifie les restrictions de vente Amazon via SP-API",
    version="1.0.0",
)

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(asin.router, prefix="/api/v1", tags=["ASIN"])


@app.get("/")
def root():
    return {"status": "ok", "message": "ASIN Restriction Checker API"}